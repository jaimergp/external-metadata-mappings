"""
Streamlit app to browse the registry and mappings
"""

import json
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


@st.cache_resource
def registry():
    return json.loads((DATA / "registry.json").read_text())


@st.cache_resource
def ecosystems():
    return sorted([f.name.rsplit(".", 2)[0] for f in DATA.glob("*.mapping.json")])


def all_purls(purltype: str = None):
    for d in registry()["definitions"]:
        if purltype == "Generic" and d["id"].startswith("pkg:generic/"):
            yield d["id"]
        elif purltype == "Virtual" and d["id"].startswith("virtual:"):
            yield d["id"]
        elif purltype == "Other" and not d["id"].startswith(("virtual:", "pkg:generic/")):
            yield d["id"]
        elif not purltype:
            yield d["id"]


@st.cache_resource
def mapping(ecosystem):
    return json.loads((DATA / f"{ecosystem}.mapping.json").read_text())


def mappings_for_purl(purl, ecosystem):
    for m in mapping(ecosystem).get("mappings", ()):
        if m["id"] == purl:
            yield m

with st.sidebar:
    purltype = st.segmented_control("Filter by PURL type", options=["Virtual", "Generic", "Other"])
    purl = st.selectbox("PURL", options=["", *sorted(all_purls(purltype))])
    ecosystem = st.selectbox("Ecosystem", options=["", *ecosystems()])

if purl and ecosystem:
    found_mappings = [
        m
        for m in mappings_for_purl(purl, ecosystem)
        if m.get("specs") or m.get("specs_from")
    ]
    st.write(f"# `{purl}`")
    st.write(f"{len(found_mappings)} mapping(s) found.")
    for m in found_mappings:
        st.write("---")
        if m["description"]:
            st.write(m["description"])
        if m["specs"]:
            st.write("- Available as:")
            st.code(json.dumps(m["specs"], indent=2), language="json")
        else:
            st.write("Not available in this ecosystem.")
elif purl:
    provided_by = []
    for d in registry()["definitions"]:
        if d["id"] == purl:
            st.write(f"### `{d["id"]}`")
            st.write(f"{d["description"] or "_no description_"}")
            if d.get("provides"):
                st.write("Provides:")
                for prov in d["provides"]:
                    st.write(f"- `{prov}`")
        if purl in d.get("provides", ()):
            provided_by.append(d["id"])
    if provided_by:
        st.write("Provided by:")
        for prov in provided_by:
            st.write(f"- `{prov}`")

else:
    definitions = registry()["definitions"]
    st.write(f"We found {len(definitions)} definitions:")
    for i, d in enumerate(definitions, 1):
        st.write(f"### {i}. `{d["id"]}`")
        st.write(f"{d["description"] or "_no description_"}")
        if d.get("provides"):
            st.write("Provides:")
            for prov in d["provides"]:
                st.write(f"- `{prov}`")
