"""
Streamlit app to browse the registry and mappings
"""

import json
import shlex
from pathlib import Path

import streamlit as st

HERE = Path(__file__).parent
DATA = HERE / "data"
SCHEMAS = HERE / "schemas"


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


def registry():
    return json.loads((DATA / "registry.json").read_text())


def ecosystems():
    return sorted([f.name.rsplit(".", 2)[0] for f in DATA.glob("*.mapping.json")])


def all_purls():
    for d in registry()["definitions"]:
        yield d["id"]


@st.cache_resource
def mapping(ecosystem):
    return json.loads((DATA / f"{ecosystem}.mapping.json").read_text())


def mappings_for_purl(purl, ecosystem):
    for m in mapping(ecosystem).get("mappings", ()):
        if m["id"] == purl and m.get("specs") or m.get("specs_from"):
            yield m


def goto(**params):
    st.session_state.initialized = False
    st.query_params.clear()
    st.query_params.update(params)


def parse_url():
    params = st.query_params.to_dict()
    purl = params.pop("purl", None)
    ecosystem = params.pop("ecosystem", None)
    if params:
        st.warning(f"URL contains unknown elements: {st.query_params.to_dict}")
        st.stop()
    return {"purl": purl, "ecosystem": ecosystem}


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
    purl = st.selectbox(
        "PURL",
        options=sorted(all_purls()),
        index=None,
        key="purl",
        placeholder="Choose a PURL identifier",
    )
    ecosystem = st.selectbox(
        "Ecosystem",
        options=[eco for eco in ecosystems() if list(mappings_for_purl(purl, eco))]
        if purl
        else [],
        index=None,
        key="ecosystem",
        placeholder="Choose a target ecosystem",
        help="Target ecosystem for which to show the mapping. Only enabled if mappings are found.",
    )

# Mappings detail page
if purl and ecosystem:
    st.query_params.clear()
    st.query_params.purl = purl
    st.query_params.ecosystem = ecosystem
    this_mapping = mapping(ecosystem)
    found_mappings = list(mappings_for_purl(purl, ecosystem))
    st.write(f"# `{purl}`")
    st.write(f"{len(found_mappings)} mapping(s) found for {ecosystem.title()}")
    for m in found_mappings:
        st.write("---")
        if m["description"]:
            st.write(m["description"])
        if m["specs"]:
            if hasattr(m["specs"], "items"):
                run_specs = (
                    m["specs"].get("run")
                    or m["specs"].get("build")
                    or m["specs"].get("host")
                    or ()
                )
            else:
                run_specs = m["specs"]
            if isinstance(run_specs, str):
                run_specs = [run_specs]
            managers = this_mapping["package_managers"]
            if len(managers) > 1:
                st.write("**Install with:**")
                for manager, tab in zip(
                    managers, st.tabs([m["name"] for m in managers])
                ):
                    tab.write(
                        f"```\n{shlex.join([*manager['install_command'], *run_specs])}\n```"
                    )
            else:
                st.write(f"**Install with `{managers[0]["name"]}`:**")
                st.write(
                    f"```\n{shlex.join([*managers[0]['install_command'], *run_specs])}\n```"
                )

            with st.expander("Raw data"):
                st.code(json.dumps(m, indent=2), language="json")
        else:
            st.write("Not available in this ecosystem.")
# Identifier detail page
elif purl:
    st.query_params.clear()
    st.query_params.purl = purl
    provided_by = []
    for d in registry()["definitions"]:
        if d["id"] == purl:
            st.write(f"### `{d["id"]}`")
            st.write(f"{d["description"] or "_no description_"}")
            if provides := d.get("provides"):
                if isinstance(provides, str):
                    provides = [provides]
                st.write("Provides:")
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
        st.write("Provided by:")
        for prov in provided_by:
            st.button(
                prov,
                key=f"{d}-{prov}-by",
                on_click=goto,
                kwargs={"purl": prov},
                icon="🔗",
            )
# All identifiers list
else:
    st.query_params.clear()
    definitions = registry()["definitions"]
    canonical, providers = [], []
    for d in definitions:
        if d.get("provides"):
            providers.append(d)
        else:
            canonical.append(d)
    st.write(f"We found {len(canonical)} canonical definitions.")
    for can in canonical:
        st.write(f"### `{can["id"]}`")
        st.write(f"{can["description"] or "_no description_"}")
        provided_by = []
        for provider in providers:
            provides = provider["provides"]
            if isinstance(provides, str):
                provides = [provides]
            if can["id"] in provides:
                provided_by.append(provider["id"])
        if provided_by:
            st.write("Provided by:")
            for prov in provided_by:
                st.button(
                    prov,
                    key=f"{can}-{prov}",
                    on_click=goto,
                    kwargs={"purl": prov},
                    icon="🔗",
                )
