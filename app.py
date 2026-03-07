import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from datetime import datetime
import pandas as pd

from config import ANTHROPIC_API_KEY
from rag.pdf_processor import process_pdf
from rag.vector_store import upsert_chunks, list_ingested_files, delete_file_chunks, reset_collection
from rag.retriever import retrieve_context
from rag.llm_client import ask_claude
from extraction.concept_extractor import extract_concepts, merge_concepts_across_files
from export.document_builder import build_docx

# ─── Page Configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Co-Creation Decision Support",
    page_icon="📚",
    layout="wide",
)

# ─── Session State Initialization ──────────────────────────────────────────────

if "qa_history" not in st.session_state:
    st.session_state.qa_history = []
if "concepts" not in st.session_state:
    st.session_state.concepts = {}
if "ingested_files" not in st.session_state:
    # Sync with what's actually in ChromaDB on startup
    try:
        st.session_state.ingested_files = list_ingested_files()
    except Exception:
        st.session_state.ingested_files = []

# ─── Header ────────────────────────────────────────────────────────────────────

st.title("Co-Creation in Education — Decision Support")
st.caption(
    "This tool answers your questions strictly based on the scientific literature you upload. "
    "All definitions, terms, and concepts are drawn exclusively from those sources."
)

if not ANTHROPIC_API_KEY:
    st.error(
        "**ANTHROPIC_API_KEY not configured.** "
        "Create a `.env` file in the project directory with:\n```\nANTHROPIC_API_KEY=sk-ant-...\n```"
    )
    st.stop()

# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Literature")

    uploaded_files = st.file_uploader(
        "Upload scientific articles (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more PDF files containing scientific literature on co-creation in education.",
    )

    if st.button("Process uploaded files", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Please select one or more PDF files first.")
        else:
            progress_bar = st.progress(0, text="Processing...")
            for i, f in enumerate(uploaded_files):
                progress_bar.progress(
                    (i) / len(uploaded_files),
                    text=f"Processing: {f.name}",
                )
                file_bytes = f.read()

                # Extract and chunk
                chunks, is_empty = process_pdf(file_bytes, f.name)

                if is_empty:
                    st.warning(
                        f"**{f.name}** contains no extractable text. "
                        "This may be a scanned PDF. Please use an OCR tool first."
                    )
                    continue

                # Embed and store
                upsert_chunks(chunks)

                # Extract concepts (separate LLM call)
                with st.spinner(f"Extracting concepts from {f.name}..."):
                    concepts = extract_concepts(f.name, chunks)
                    st.session_state.concepts[f.name] = concepts

                if f.name not in st.session_state.ingested_files:
                    st.session_state.ingested_files.append(f.name)

            progress_bar.progress(1.0, text="Done!")
            st.success(f"Processed {len(uploaded_files)} file(s) successfully.")
            st.rerun()

    st.divider()
    st.subheader("Indexed Literature")

    if not st.session_state.ingested_files:
        st.info("No literature indexed yet.")
    else:
        for fname in st.session_state.ingested_files:
            col1, col2 = st.columns([5, 1])
            col1.markdown(f"📄 {fname}")
            if col2.button("✕", key=f"del_{fname}", help=f"Remove {fname}"):
                delete_file_chunks(fname)
                st.session_state.ingested_files = [
                    f for f in st.session_state.ingested_files if f != fname
                ]
                if fname in st.session_state.concepts:
                    del st.session_state.concepts[fname]
                st.rerun()

    st.divider()
    if st.button("Reset all literature", type="secondary", use_container_width=True):
        reset_collection()
        st.session_state.ingested_files = []
        st.session_state.concepts = {}
        st.session_state.qa_history = []
        st.rerun()

# ─── Main Tabs ─────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["Ask a Question", "Key Concepts", "Export Session"])

# ── Tab 1: Ask a Question ──────────────────────────────────────────────────────

with tab1:
    st.header("Ask a Question about the Literature")

    if not st.session_state.ingested_files:
        st.warning(
            "No literature indexed yet. Upload and process PDF files using the sidebar."
        )
    else:
        sources_list = ", ".join(st.session_state.ingested_files)
        st.info(f"**Available literature:** {sources_list}")

    question = st.text_area(
        "Your question:",
        placeholder=(
            "E.g.: How do the authors define co-creation in higher education? "
            "What are the key conditions for successful co-creation?"
        ),
        height=120,
        disabled=not st.session_state.ingested_files,
    )

    submit = st.button(
        "Get Answer",
        type="primary",
        disabled=not st.session_state.ingested_files or not question.strip(),
    )

    if submit and question.strip():
        with st.spinner("Searching literature and generating answer..."):
            retrieval = retrieve_context(question)

            if not retrieval["has_results"]:
                st.warning(
                    "No relevant fragments found in the indexed literature for this question. "
                    "Try rephrasing your question or upload additional literature."
                )
            else:
                response = ask_claude(question, retrieval["context_block"])

                entry = {
                    "question": question,
                    "answer": response["answer"],
                    "sources": retrieval["sources"],
                    "timestamp": datetime.now().strftime("%d %B %Y, %H:%M"),
                    "tokens": response["input_tokens"] + response["output_tokens"],
                }
                st.session_state.qa_history.insert(0, entry)
                st.rerun()

    # Q&A History
    if st.session_state.qa_history:
        st.divider()
        st.subheader("Previous Questions & Answers")

        for i, qa in enumerate(st.session_state.qa_history):
            label = qa["question"][:90] + ("..." if len(qa["question"]) > 90 else "")
            with st.expander(f"Q{len(st.session_state.qa_history) - i}: {label}", expanded=(i == 0)):
                st.markdown(f"**Question:** {qa['question']}")
                st.divider()
                st.markdown(qa["answer"])
                st.caption(f"Asked: {qa.get('timestamp', '')} · Tokens used: {qa.get('tokens', 0)}")

# ── Tab 2: Key Concepts ────────────────────────────────────────────────────────

with tab2:
    st.header("Key Concepts from the Literature")

    if not st.session_state.concepts:
        st.info(
            "No concepts available yet. Upload and process literature using the sidebar. "
            "Concepts are extracted automatically after each upload."
        )
    else:
        filter_options = ["All sources"] + list(st.session_state.concepts.keys())
        selected_source = st.selectbox("Filter by source:", filter_options)

        if selected_source == "All sources":
            concepts_to_show = merge_concepts_across_files(st.session_state.concepts)
        else:
            concepts_to_show = st.session_state.concepts.get(selected_source, [])

        if not concepts_to_show:
            st.info("No concepts found for this source.")
        else:
            st.markdown(f"**{len(concepts_to_show)} concept(s) found**")

            # Table view
            df_data = [
                {
                    "Term": c.get("term", ""),
                    "Definition": c.get("definition", ""),
                    "Source": c.get("source_filename", ""),
                }
                for c in concepts_to_show
            ]
            st.dataframe(
                pd.DataFrame(df_data),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("Concept Details")

            for concept in concepts_to_show:
                with st.expander(f"**{concept.get('term', 'Unknown')}**"):
                    if concept.get("definition"):
                        st.markdown(f"**Definition:** {concept['definition']}")
                    if concept.get("context"):
                        st.markdown(f"**Context:** {concept['context']}")
                    if concept.get("exact_quote"):
                        st.markdown("**Exact quote from source:**")
                        st.markdown(f"> {concept['exact_quote']}")
                    st.caption(f"Source: {concept.get('source_filename', '')}")

# ── Tab 3: Export Session ──────────────────────────────────────────────────────

with tab3:
    st.header("Export This Session")

    if not st.session_state.qa_history and not st.session_state.concepts:
        st.info(
            "Ask questions and/or upload literature to generate content before exporting."
        )
    else:
        session_title = st.text_input(
            "Document title:",
            value=f"Co-Creation Decision Support Report — {datetime.now().strftime('%B %d, %Y')}",
        )

        st.subheader("Session Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Literature files", len(st.session_state.ingested_files))
        col2.metric("Key concepts", sum(len(v) for v in st.session_state.concepts.values()))
        col3.metric("Questions answered", len(st.session_state.qa_history))

        st.divider()

        with st.spinner("Building document..."):
            docx_bytes = build_docx(
                session_title=session_title,
                uploaded_files=st.session_state.ingested_files,
                concepts=st.session_state.concepts,
                qa_history=st.session_state.qa_history,
            )

        filename = f"co_creation_report_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
        st.download_button(
            label="Download as Word (.docx)",
            data=docx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True,
        )

        st.caption(
            "The document includes: uploaded literature list, key concepts table, "
            "all questions and answers with citations, and a references section."
        )

        # Preview
        if st.session_state.qa_history:
            st.divider()
            st.subheader("Preview")
            for i, qa in enumerate(st.session_state.qa_history, start=1):
                st.markdown(f"**Question {i}:** {qa['question']}")
                st.markdown(qa["answer"])
                st.divider()
