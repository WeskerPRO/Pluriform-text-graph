import sys
import os

# Add project root to path so we can import textlpg
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from textlpg.queries import (
    get_all_books,
    get_chapters,
    get_verses,
    get_languages,
    # get_verse_text,
    get_chapter_text,
    compare_verse,
    search_verses_case_insensitive,
    get_database_stats,
    get_book_stats,
    get_annotations,
)
from textlpg.enrich import enrich_verse, PROMPTS
from textlpg.nl_query import nl_query
from textlpg.agent_query import agent_query


# ── Page Config ──────────────────────────────────────────
st.set_page_config(
    page_title="TextLPG",
    page_icon="📖",
    layout="wide",
)

st.title("📖 TextLPG")
st.caption("Modeling pluriform texts as a Labeled Property Graph")


# ── Sidebar — Database Stats ─────────────────────────────
with st.sidebar:
    st.header("Database")
    try:
        stats = get_database_stats()
        for label, count in stats["nodes"].items():
            st.metric(f":{label}", f"{count:,}")
    except Exception as e:
        st.error(f"Cannot connect to Neo4j: {e}")
        st.stop()


# ── Tabs ─────────────────────────────────────────────────
tab_browse, tab_read, tab_compare, tab_search, tab_enrich, tab_nlq, tab_agent = st.tabs([
    "📚 Browse", "📖 Read", "🔀 Compare", "🔍 Search", "🤖 Enrich", "💬 Ask", "🤖 Agent"
])


# ══════════════════════════════════════════════════════════
# TAB 1: Browse — explore the book/chapter/verse hierarchy
# ══════════════════════════════════════════════════════════
with tab_browse:
    st.subheader("Browse the Bible structure")

    # List books
    book_options = {b["code"]: b["id"] for b in get_all_books()}
    selected_book = st.selectbox("Book", list(book_options.keys()), key="browse_book")

    if selected_book:
        # Show book stats
        book_info = get_book_stats(selected_book)
        if book_info:
            col1, col2, col3 = st.columns(3)
            col1.metric("Chapters", book_info["chapters"])
            col2.metric("Verses", book_info["verses"])
            col3.metric("Languages", book_info["languages"])

        # List chapters
        chapters = get_chapters(selected_book)
        if chapters:
            ch_numbers = [ch["number"] for ch in chapters]
            selected_ch = st.selectbox("Chapter", ch_numbers, key="browse_chapter")

            if selected_ch:
                chapter_id = f"b.{selected_book}.{selected_ch}"
                verses = get_verses(chapter_id)
                if verses:
                    st.write(f"**{len(verses)} verses** in {selected_book} {int(selected_ch)}")
                    verse_data = [{"Verse": v["number"], "ID": v["id"]} for v in verses]
                    st.dataframe(verse_data, width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════
# TAB 2: Read — get verse content in a language
# ══════════════════════════════════════════════════════════
with tab_read:
    st.subheader("Read verses")

    col1, col2 = st.columns(2)

    with col1:
        books_read = get_all_books()
        book_codes = [b["code"] for b in books_read]
        read_book = st.selectbox("Book", book_codes, key="read_book")

    with col2:
        languages = get_languages()
        read_lang = st.selectbox("Language", languages, key="read_lang", index=languages.index("en") if "en" in languages else 0)

    if read_book:
        chapters_read = get_chapters(read_book)
        ch_numbers = [ch["number"] for ch in chapters_read]
        read_ch = st.selectbox("Chapter", ch_numbers, key="read_chapter")

        if read_ch and read_lang:
            results = get_chapter_text(read_book, read_ch, read_lang)
            if results:
                st.write(f"**{read_book} {int(read_ch)}** — {read_lang} ({len(results)} verses)") # len(results)
                st.divider()
                for r in results:
                    st.markdown(f"**{int(r['verse'])}** {r['content']}")
            else:
                st.warning(f"No content found for {read_book} {read_ch} in '{read_lang}'")


# ══════════════════════════════════════════════════════════
# TAB 3: Compare — verse across languages
# ══════════════════════════════════════════════════════════
with tab_compare:
    st.subheader("Compare a verse across languages")

    col1, col2, col3 = st.columns(3)
    with col1:
        cmp_book = st.selectbox("Book", [b["code"] for b in get_all_books()], key="cmp_book")
    with col2:
        if cmp_book:
            cmp_chapters = get_chapters(cmp_book)
            cmp_ch = st.selectbox("Chapter", [ch["number"] for ch in cmp_chapters], key="cmp_ch")
    with col3:
        if cmp_book and cmp_ch:
            cmp_verses_list = get_verses(f"b.{cmp_book}.{cmp_ch}")
            cmp_verse = st.selectbox("Verse", [v["number"] for v in cmp_verses_list], key="cmp_verse")

    langs = get_languages()
    selected_langs = st.multiselect("Languages to compare", langs, default=["en", "de", "fr"] if all(l in langs for l in ["en", "de", "fr"]) else langs[:3], key="cmp_langs")

    if cmp_book and cmp_ch and cmp_verse and selected_langs:
        verse_id = f"b.{cmp_book}.{cmp_ch}.{cmp_verse}"
        if st.button("Compare", key="cmp_btn"):
            results = compare_verse(verse_id, selected_langs)
            if results:
                for r in results:
                    st.info(f"**[{r['language']}]** {r['content']}")
            else:
                st.warning("No results found")


# ══════════════════════════════════════════════════════════
# TAB 4: Search — find verses by keyword
# ══════════════════════════════════════════════════════════
with tab_search:
    st.subheader("Search verses by keyword")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword = st.text_input("Keyword", placeholder="e.g., love, light, faith", key="search_kw")
    with col2:
        search_lang = st.selectbox("Language", get_languages(), key="search_lang", index=get_languages().index("en") if "en" in get_languages() else 0)
    with col3:
        search_limit = st.number_input("Max results", min_value=1, max_value=100, value=20, key="search_limit")

    if keyword:
        results = search_verses_case_insensitive(keyword, language=search_lang, limit=search_limit)
        if results:
            st.write(f"**{len(results)} results** for \"{keyword}\" in {search_lang}")
            st.divider()
            for r in results:
                # Highlight the keyword in the content
                content = r["content"]
                st.markdown(f"**{r['verse_id']}** — {content}")
        else:
            st.warning(f"No results for \"{keyword}\" in {search_lang}")


# ══════════════════════════════════════════════════════════
# TAB 5: Enrich — generate LLM annotations
# ══════════════════════════════════════════════════════════
with tab_enrich:
    st.subheader("LLM Enrichment")
    st.caption("Generate annotations using gemma2:9b via Ollama")

    col1, col2 = st.columns(2)
    with col1:
        enrich_verse_id = st.text_input("Verse ID", value="b.GEN.001.001", key="enrich_vid")
    with col2:
        enrich_type = st.selectbox("Annotation type", list(PROMPTS.keys()), key="enrich_type")

    if st.button("Generate annotation", key="enrich_btn"):
        with st.spinner(f"Asking gemma2:9b to generate {enrich_type}..."):
            try:
                result = enrich_verse(enrich_verse_id, enrich_type)
                if result:
                    st.success(f"Annotation saved: {result['annotation_id']}")
                    st.info(f"**[{result['type']}]** {result['content']}")
                else:
                    st.error("Failed — verse not found or LLM error")
            except Exception as e:
                st.error(f"Error: {e}")
                st.caption("Make sure Ollama is running: `ollama serve`")

    # Show existing annotations
    st.divider()
    st.write("**Existing annotations for this verse:**")
    if enrich_verse_id:
        annotations = get_annotations(enrich_verse_id)
        if annotations:
            for a in annotations:
                st.markdown(f"- **[{a['type']}]** ({a['author']}) — {a['content']}")
        else:
            st.caption("No annotations yet")


# ══════════════════════════════════════════════════════════
# TAB 6: Ask — natural language queries
# ══════════════════════════════════════════════════════════
with tab_nlq:
    st.subheader("Ask in natural language")
    st.caption("Your question is converted to Cypher by gemma2:9b, then executed on Neo4j")

    question = st.text_input("Your question", placeholder="e.g., How many books are in the Bible?", key="nlq_question")

    if st.button("Ask", key="nlq_btn") and question:
        with st.spinner("Generating Cypher query..."):
            try:
                result = nl_query(question)

                # Show the generated Cypher
                st.code(result["cypher"], language="cypher")
                st.caption(f"LLM: {result['llm_time']:.1f}s | DB: {result.get('db_time', 0):.3f}s")

                # Show results
                if "error" in result:
                    st.error(f"Query failed: {result['error']}")
                elif result["results"]:
                    st.dataframe(result["results"], width="stretch", hide_index=True)
                else:
                    st.warning("No results returned")
            except Exception as e:
                st.error(f"Error: {e}")
                st.caption("Make sure Ollama is running")


# ══════════════════════════════════════════════════════════
# TAB 7: Agent — self-healing agentic queries
# ══════════════════════════════════════════════════════════
with tab_agent:
    st.subheader("Agentic Query (Self-Healing)")
    st.caption("Like 'Ask', but the agent automatically retries and fixes failed Cypher queries")

    col1, col2 = st.columns([4, 1])
    with col1:
        agent_question = st.text_input("Your question", placeholder="e.g., Compare Psalm 23:1 in English and French", key="agent_question")
    with col2:
        agent_retries = st.number_input("Max retries", min_value=1, max_value=5, value=3, key="agent_retries")

    if st.button("Ask Agent", key="agent_btn") and agent_question:
        with st.spinner("Agent is working (may retry on errors)..."):
            try:
                result = agent_query(agent_question, max_retries=agent_retries, verbose=False)

                # Show attempt history
                for i, attempt in enumerate(result["attempts"]):
                    with st.expander(f"Attempt {attempt['attempt']} — {'Success' if attempt['success'] else 'Failed'}", expanded=(i == len(result["attempts"]) - 1)):
                        st.code(attempt["cypher"], language="cypher")
                        if attempt["error"]:
                            st.error(f"Error: {attempt['error'][:200]}")
                        st.caption(f"LLM: {attempt['llm_time']:.1f}s")

                # Final result
                st.divider()
                if result["success"]:
                    st.success(f"Success in {result['total_attempts']} attempt(s) | Total: {result['total_time']:.1f}s")
                    st.dataframe(result["results"], width="stretch", hide_index=True)
                else:
                    st.error(f"Failed after {result['total_attempts']} attempts ({result['total_time']:.1f}s)")

            except Exception as e:
                st.error(f"Error: {e}")
                st.caption("Make sure Ollama is running")
