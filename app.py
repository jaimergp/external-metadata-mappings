"""
Streamlit app to browse the registry and mappings
"""

import json
import shlex
from pathlib import Path

import streamlit as st

from external_metadata_mappings import Registry, Mapping

HERE = Path(__file__).parent
DATA = HERE / "data"
SCHEMAS = HERE / "schemas"
REGISTRY = Registry.from_path(DATA / "registry.json")

st.set_page_config(
    page_title="PEP-725 registry and mappings browser",
    page_icon="📦",
    initial_sidebar_state="expanded",
    menu_items={
        "about": """
        **📦 PEP725-metadata-browser **

        Explore the central registry of PURL identifiers and their mapped names
        in several ecosystems.
        """
    },
)


def ecosystems():
    return sorted([f.name.rsplit(".", 2)[0] for f in DATA.glob("*.mapping.json")])


def mapping_for(ecosystem):
    return Mapping.from_path(DATA / f"{ecosystem}.mapping.json")


def goto(**params):
    st.session_state.initialized = False
    st.query_params.clear()
    st.query_params.update(params)


def parse_url():
    params = st.query_params.to_dict()
    purl = params.pop("purl", None)
    ecosystem = params.pop("ecosystem", None)
    if params:
        st.warning(f"URL contains unknown elements: {params}")
        st.stop()
    return {"purl": purl, "ecosystem": ecosystem}


def render_description(definition: str):
    if description := definition.get("description"):
        st.write("\n".join([f"> {line}" for line in description.splitlines()]))
    else:
        st.write("> _No description_")


def render_urls(definition):
    if urls := definition.get("urls"):
        st.write("**🔗 Links:**")
        if hasattr(urls, "items"):
            for name, url in urls.items():
                st.write(f"- [{name}]({url})")
        else:
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                st.write(f"- [{url}]({url})")


url_params = parse_url()
if not getattr(st.session_state, "initialized", False):
    initialized = False
    for param, value in url_params.items():
        if value:
            setattr(st.session_state, param, value)
            initialized = True
    if initialized:
        st.session_state.initialized = initialized


with st.sidebar:
    st.write("# External mappings browser")
    available_purls = list(REGISTRY.iter_unique_purls())
    purl = st.selectbox(
        f"PURL ({len(available_purls)} available)",
        options=available_purls,
        index=None,
        key="purl",
        placeholder="Choose a PURL identifier",
    )
    eco_options = (
        [
            eco
            for eco in ecosystems()
            if list(mapping_for(eco).iter_by_id(purl, only_mapped=True))
        ]
        if purl
        else ecosystems()
    )
    ecosystem = st.selectbox(
        "Ecosystem",
        options=eco_options,
        format_func=lambda value: mapping_for(value).name,
        index=None,
        key="ecosystem",
        placeholder=f"{len(eco_options)} mappings available"
        if purl
        else "Or browse a mapping",
    )

# Mappings detail page
if purl and ecosystem:
    st.query_params.clear()
    st.query_params.purl = purl
    st.query_params.ecosystem = ecosystem
    full_mapping = mapping_for(ecosystem)
    st.write(f"# {full_mapping.name}")
    render_description(full_mapping)
    st.write(f"## `{purl}`")
    found_mapping_entries = list(full_mapping.iter_by_id(purl, only_mapped=True))
    st.write(f"{len(found_mapping_entries)} mapping(s) found:")
    for i, m in enumerate(found_mapping_entries, 1):
        st.write(f"### {i}")
        render_description(m)
        render_urls(m)
        if m["specs"]["run"]:
            managers = full_mapping.get("package_managers", ())
            if len(managers) > 1:
                st.write("**📦 Install with:**")
                for manager, tab in zip(
                    managers, st.tabs([m["name"] for m in managers])
                ):
                    command = full_mapping.build_install_command(
                        manager["install_command"],
                        m["specs"]["run"],
                        manager["requires_elevation"],
                    )
                    tab.write(f"```\n{shlex.join(command)}\n```")
            else:
                st.write(f"**Install with `{managers[0]['name']}`:**")
                command = full_mapping.build_install_command(
                    managers[0]["install_command"],
                    m["specs"]["run"],
                    managers[0]["requires_elevation"],
                )
                st.write(f"```\n{shlex.join(command)}\n```")
            with st.expander("Raw data"):
                st.code(json.dumps(m, indent=2), language="json")
        else:
            st.write("Not available in this ecosystem.")
        st.write("---")
# Identifier detail page
elif purl:
    st.query_params.clear()
    st.query_params.purl = purl
    provided_by = []
    for d in REGISTRY.iter_all():
        if d["id"] == purl:
            st.write(f"### `{d['id']}`")
            render_description(d)
            render_urls(d)
            if provides := d.get("provides"):
                if isinstance(provides, str):
                    provides = [provides]
                st.write("**📤 Provides:**")
                for prov in provides:
                    st.button(
                        prov,
                        key=f"{d}-{prov}",
                        on_click=goto,
                        kwargs={"purl": prov},
                        icon="🔗",
                    )
        if purl in d.get("provides", ()):
            provided_by.append(d["id"])
    if provided_by:
        st.write("**📥 Provided by:**")
        for prov in provided_by:
            st.button(
                prov,
                key=f"{d}-{prov}-by",
                on_click=goto,
                kwargs={"purl": prov},
                icon="🔗",
            )
    if available_ecos := [
        eco
        for eco in ecosystems()
        if list(mapping_for(eco).iter_by_id(purl, only_mapped=True))
    ]:
        st.write("**📍 Mappings found for:**")
        for eco in available_ecos:
            st.button(
                mapping_for(eco).name,
                key=f"{d}-{purl}-{eco}",
                on_click=goto,
                kwargs={"purl": purl, "ecosystem": eco},
                icon="🔗",
            )
elif ecosystem:
    st.query_params.clear()
    st.query_params.ecosystem = ecosystem
    full_mapping = mapping_for(ecosystem)
    st.write(f"# {full_mapping.get('name') or ecosystem}")
    render_description(full_mapping)
    all_mappings = list(full_mapping.iter_all())
    filled_mappings, empty_mappings = [], []
    for m in all_mappings:
        if m.get("specs"):
            filled_mappings.append(m)
        else:
            empty_mappings.append(m)
    unique_ids = list(dict.fromkeys([m["id"] for m in filled_mappings]))
    st.write(
        f"Found **{len(all_mappings)}** mapping entries, "
        f"of which **{len(filled_mappings)}** are fully specified, "
        f"which correspond to **{len(unique_ids)}** unique IDs:"
    )
    for m in unique_ids:
        st.button(
            m,
            key=m,
            on_click=goto,
            kwargs={"purl": m, "ecosystem": ecosystem},
            icon="🔗",
        )
    if empty_mappings:
        st.write("The following entries are not mapped:")
        for m in empty_mappings:
            st.button(
                m["id"],
                key=m["id"],
                on_click=goto,
                kwargs={"purl": m["id"]},
                icon="🔗",
            )
# All identifiers list
else:
    st.query_params.clear()
    canonical, providers = {"generic": [], "virtual": []}, []
    count = 0
    for d in REGISTRY.iter_all():
        if provides := d.get("provides"):
            if isinstance(provides, str):
                provides = [provides]
            if any(item.startswith("pkg:") for item in provides):
                providers.append(d)
        elif d["id"].startswith("pkg:generic/"):
            canonical["generic"].append(d)
            count += 1
        else:
            canonical["virtual"].append(d)
            count += 1
    st.write("# Canonical identifiers")
    st.write(
        f"We found {count} canonical definitions. "
        "Non-canonical definitions are listed in the dropdown menu by the sidebar."
    )
    generic_tab, virtual_tab = st.tabs(
        [
            f"Generic ({len(canonical['generic'])})",
            f"Virtual ({len(canonical['virtual'])})",
        ]
    )
    tabs = {"generic": generic_tab, "virtual": virtual_tab}
    for tab, values in canonical.items():
        with tabs[tab]:
            for value in values:
                st.write(f"## `{value['id']}`")
                render_description(value)
                render_urls(value)
                st.button(
                    "View details",
                    key=f"{value['id']}",
                    on_click=goto,
                    kwargs={"purl": value["id"]},
                    icon="➕",
                )
