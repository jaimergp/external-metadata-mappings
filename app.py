"""
Streamlit app to browse the registry and mappings
"""

import json
import shlex
from pathlib import Path

import streamlit as st

from pyproject_external import Registry, Mapping
from pyproject_external._registry import PackageManager, MappedSpec

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

        Explore the central registry of package identifiers and their mapped names
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
    id_ = params.pop("id", None)
    ecosystem = params.pop("ecosystem", None)
    if params:
        st.warning(f"URL contains unknown elements: {params}")
        st.stop()
    return {"id": id_, "ecosystem": ecosystem}


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
    available_dep_urls = list(REGISTRY.iter_unique_ids())
    dep_url = st.selectbox(
        f"Identifier ({len(available_dep_urls)} available)",
        options=available_dep_urls,
        index=None,
        key="id",
        placeholder="Choose a package",
    )
    eco_options = (
        [
            eco
            for eco in ecosystems()
            if list(mapping_for(eco).iter_by_id(dep_url, only_mapped=True))
        ]
        if dep_url
        else ecosystems()
    )
    ecosystem = st.selectbox(
        "Ecosystem",
        options=eco_options,
        format_func=lambda value: mapping_for(value).name,
        index=None,
        key="ecosystem",
        placeholder=f"{len(eco_options)} mappings available"
        if dep_url
        else "Or browse a mapping",
    )

# Mappings detail page
if dep_url and ecosystem:
    st.query_params.clear()
    st.query_params.id = dep_url
    st.query_params.ecosystem = ecosystem
    full_mapping = mapping_for(ecosystem)
    st.write(f"# {full_mapping.name}")
    render_description(full_mapping)
    st.write(f"## `{dep_url}`")
    found_mapping_entries = list(full_mapping.iter_by_id(dep_url, only_mapped=True))
    st.write(f"{len(found_mapping_entries)} mapping(s) found:")
    for i, m in enumerate(found_mapping_entries, 1):
        st.write(f"### {i}")
        render_description(m)
        render_urls(m)
        if m["specs"]["run"]:
            specs = [MappedSpec(spec, "") for spec in m["specs"]["run"]]
            managers = full_mapping.get("package_managers", ())
            for text, command_type in (
                ("📦 Install", "install"),
                ("🔎 Query", "query"),
            ):
                if len(managers) > 1:
                    st.write(f"**{text} with:**")
                    for manager, tab in zip(
                        managers, st.tabs([m["name"] for m in managers])
                    ):
                        mgr = PackageManager.from_mapping_entry(manager)
                        commands = list(mgr.render_commands(command_type, specs))
                        text = "\n".join([shlex.join(command) for command in commands])
                        tab.write(f"```\n{text}\n```")
                else:
                    st.write(f"**{text} with `{managers[0]['name']}`:**")
                    mgr = PackageManager.from_mapping_entry(managers[0])
                    commands = list(mgr.render_commands(command_type, specs))
                    text = "\n".join([shlex.join(command) for command in commands])
                    st.write(f"```\n{text}\n```")
            with st.expander("Raw data"):
                st.code(json.dumps(m, indent=2), language="json")
        else:
            st.write("Not available in this ecosystem.")
        st.write("---")
# Identifier detail page
elif dep_url:
    st.query_params.clear()
    st.query_params.id = dep_url
    provided_by = []
    for d in REGISTRY.iter_all():
        if d["id"] == dep_url:
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
                        kwargs={"id": prov},
                        icon="🔗",
                    )
        if dep_url in d.get("provides", ()):
            provided_by.append(d["id"])
    if provided_by:
        st.write("**📥 Provided by:**")
        for prov in provided_by:
            st.button(
                prov,
                key=f"{d}-{prov}-by",
                on_click=goto,
                kwargs={"id": prov},
                icon="🔗",
            )
    if available_ecos := [
        eco
        for eco in ecosystems()
        if list(mapping_for(eco).iter_by_id(dep_url, only_mapped=True))
    ]:
        st.write("**📍 Mappings found for:**")
        for eco in available_ecos:
            st.button(
                mapping_for(eco).name,
                key=f"{d}-{dep_url}-{eco}",
                on_click=goto,
                kwargs={"id": dep_url, "ecosystem": eco},
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
        if any(deps for deps in m.get("specs").values()):
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
            kwargs={"id": m, "ecosystem": ecosystem},
            icon="🔗",
        )
    if empty_mappings:
        st.write(f"The following **{len(empty_mappings)}** entries are not mapped:")
        with st.expander("Not mapped"):
            for m in empty_mappings:
                st.button(
                    m["id"],
                    key=m["id"],
                    on_click=goto,
                    kwargs={"id": m["id"]},
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
            if any(item.startswith("dep:") for item in provides):
                providers.append(d)
        elif d["id"].startswith("dep:generic/"):
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
                    kwargs={"id": value["id"]},
                    icon="➕",
                )
