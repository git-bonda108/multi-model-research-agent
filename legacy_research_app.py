import os
import time
import requests
import streamlit as st
from openai import OpenAI
from tavily import TavilyClient
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
import anthropic

# Load environment variables, overriding any existing ones
load_dotenv(override=True)


class SageLensSystem:
    def __init__(self):
        try:
            # Force reload environment variables (for local development)
            load_dotenv(override=True)
            
            # Helper function to get secrets: Streamlit Cloud first, then env vars
            def get_secret(key: str, default: str = "") -> str:
                """Get secret from Streamlit secrets (Cloud) or environment variables (local)"""
                # Try Streamlit secrets first (for Streamlit Cloud)
                try:
                    if hasattr(st, 'secrets') and st.secrets is not None:
                        # Try accessing as attribute (st.secrets.KEY_NAME)
                        try:
                            value = getattr(st.secrets, key, None)
                            if value:
                                return str(value).strip().strip('"').strip("'")
                        except (AttributeError, TypeError):
                            pass
                        
                        # Try accessing as dictionary (st.secrets["KEY_NAME"])
                        try:
                            if isinstance(st.secrets, dict) and key in st.secrets:
                                value = st.secrets[key]
                                if value:
                                    return str(value).strip().strip('"').strip("'")
                        except (KeyError, TypeError):
                            pass
                except Exception:
                    # If st.secrets fails, continue to env vars
                    pass
                
                # Fall back to environment variables (for local development)
                value = os.getenv(key, default)
                return str(value).strip().strip('"').strip("'")
            
            # Get API keys using the helper function
            openai_key = get_secret("OPENAI_API_KEY")
            anthropic_key = get_secret("ANTHROPIC_API_KEY")
            tavily_key = get_secret("TAVILY_API_KEY")
            serper_key = get_secret("SERPER_API_KEY")
            
            # Validate API keys are not empty BEFORE creating clients
            errors = []
            if not openai_key:
                errors.append("OPENAI_API_KEY")
            if not anthropic_key:
                errors.append("ANTHROPIC_API_KEY")
            
            if errors:
                error_msg = f"❌ Missing required API keys: {', '.join(errors)}\n\n"
                error_msg += "📝 NEXT STEPS:\n\n"
                error_msg += "🌐 If deploying on Streamlit Cloud:\n"
                error_msg += "   1. Go to your app → Settings → Secrets\n"
                error_msg += "   2. Add these keys:\n"
                error_msg += "      [secrets]\n"
                error_msg += "      OPENAI_API_KEY = \"sk-proj-...\"\n"
                error_msg += "      ANTHROPIC_API_KEY = \"sk-ant-api03-...\"\n"
                error_msg += "   3. Click 'Save' and wait for app to restart\n\n"
                error_msg += "💻 If running locally:\n"
                error_msg += "   1. Create a .env file in the project root\n"
                error_msg += "   2. Add: OPENAI_API_KEY=\"sk-proj-...\"\n"
                error_msg += "   3. Add: ANTHROPIC_API_KEY=\"sk-ant-api03-...\"\n"
                error_msg += "   4. Restart the app\n\n"
                error_msg += "📖 See STREAMLIT_SECRETS_SETUP.md for detailed instructions"
                raise ValueError(error_msg)
            
            # Initialize OpenAI client - latest SDK uses api_key parameter
            # OpenAI SDK 2.0+ uses: OpenAI(api_key=key)
            # Only create clients if keys are valid
            self.llms = {
                "openai": OpenAI(api_key=openai_key),
                "anthropic": anthropic.Anthropic(api_key=anthropic_key)
            }
            
            # Initialize other services
            if tavily_key:
                self.tavily = TavilyClient(api_key=tavily_key)
            else:
                self.tavily = None
                
            if serper_key:
                self.serper_config = {
                    "url": "https://google.serper.dev/search",
                    "headers": {"X-API-KEY": serper_key},
                    "timeout": 10
                }
            else:
                self.serper_config = None
                
        except ValueError as e:
            # Show detailed error with next steps
            st.error(str(e))
            st.stop()  # Stop execution to prevent further errors
        except Exception as e:
            error_msg = f"❌ Initialization failed: {str(e)}\n\n"
            error_msg += "📝 NEXT STEPS:\n\n"
            error_msg += "🌐 If deploying on Streamlit Cloud:\n"
            error_msg += "   1. Go to your app → Settings → Secrets\n"
            error_msg += "   2. Add your API keys (see STREAMLIT_SECRETS_SETUP.md)\n"
            error_msg += "   3. Click 'Save' and wait for app to restart\n\n"
            error_msg += "💻 If running locally:\n"
            error_msg += "   1. Check your .env file exists and has correct keys\n"
            error_msg += "   2. Verify keys are not empty or have extra spaces\n"
            error_msg += "   3. Restart the app\n\n"
            error_msg += "📖 See STREAMLIT_SECRETS_SETUP.md for detailed instructions"
            st.error(error_msg)
            st.stop()  # Stop execution to prevent further errors

    def _search_web(self, query: str) -> list:
        all_results = []
        try:
            # Tavily Search
            if self.tavily:
                try:
                    tavily_results = self.tavily.search(query=query, max_results=5)
                    all_results.extend([
                        {"title": r.get("title", "Untitled"), "url": r["url"]}
                        for r in tavily_results.get("results", []) if "url" in r
                    ])
                except Exception as e:
                    st.warning(f"Tavily search error: {str(e)}")

            # Google Serper
            if self.serper_config:
                try:
                    response = requests.post(**self.serper_config, json={"q": query, "num": 5})
                    response.raise_for_status()
                    serper_results = response.json()
                    all_results.extend([
                        {"title": r.get("title", "Untitled"), "url": r["link"]}
                        for r in serper_results.get("organic", []) if "link" in r
                    ])
                except Exception as e:
                    st.warning(f"Serper search error: {str(e)}")

            # Deduplicate and return top results (already sorted by search relevance from APIs)
            seen = set()
            unique_results = [x for x in all_results if not (x["url"] in seen or seen.add(x["url"]))]
            # Return top 10 highest searched/most relevant links
            return unique_results[:10]
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

    def _search_videos(self, query: str) -> list:
        try:
            results = YoutubeSearch(query, max_results=10).to_dict()
            # Extract videos with views and sort by view count (highest first)
            videos = []
            for r in results:
                if 'id' in r:
                    views_str = r.get("views", "0")
                    # Parse views (handles formats like "1.2M views", "500K views", etc.)
                    try:
                        views_num = 0
                        if views_str and views_str != "N/A":
                            views_clean = views_str.replace(" views", "").replace(",", "").strip()
                            if "M" in views_clean:
                                views_num = float(views_clean.replace("M", "")) * 1000000
                            elif "K" in views_clean:
                                views_num = float(views_clean.replace("K", "")) * 1000
                            else:
                                views_num = float(views_clean) if views_clean.isdigit() else 0
                    except:
                        views_num = 0
                    
                    videos.append({
                        "title": r.get("title", "Untitled Video"),
                        "url": f"https://youtube.com/watch?v={r['id']}",
                        "views": views_str,
                        "views_num": views_num
                    })
            
            # Sort by view count (highest first) and return top 5
            videos_sorted = sorted(videos, key=lambda x: x["views_num"], reverse=True)
            return [{"title": v["title"], "url": v["url"], "views": v["views"]} for v in videos_sorted[:5]]
        except Exception as e:
            st.error(f"Video search error: {str(e)}")
            return []

    def _generate_content(self, provider: str, prompt: str) -> dict:
        try:
            start_time = time.time()
            if provider == "anthropic":
                # Anthropic SDK: client.messages.create()
                response = self.llms[provider].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=[
                        {"role": "user", "content": f"Generate a concise, comprehensive summary about: {prompt}"}
                    ]
                )
                # Anthropic response structure: response.content is a list of ContentBlock objects
                # Each block has a .text attribute
                content_text = response.content[0].text if response.content else ""
                return {
                    "content": content_text,
                    "provider": "Claude-3.5-Sonnet",
                    "latency": time.time() - start_time
                }
            else:
                # OpenAI SDK 2.0+: client.chat.completions.create()
                response = self.llms["openai"].chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "user", "content": f"Create a concise, comprehensive summary about: {prompt}"}],
                    temperature=0.3
                )
                # OpenAI response structure: response.choices[0].message.content
                return {
                    "content": response.choices[0].message.content,
                    "provider": "OpenAI-GPT4",
                    "latency": time.time() - start_time
                }
        except Exception as e:
            # More detailed error logging
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
                st.error(f"{provider} authentication error: {error_msg}")
            else:
                st.error(f"{provider} error: {error_msg}")
            return None

    def process_query(self, topic: str) -> dict:
        result = {"content": "", "references": {"web": [], "videos": []}}
        try:
            versions = []
            for provider in ["openai", "anthropic"]:
                if content := self._generate_content(provider, topic):
                    versions.append(content)
            if versions:
                result["content"] = max(versions, key=lambda x: len(x["content"]))
                result["references"]["web"] = self._search_web(topic)
                result["references"]["videos"] = self._search_videos(topic)
        except Exception as e:
            st.error(f"Processing error: {str(e)}")
        return result


def main():
    st.set_page_config(
        page_title="Sage-Lens",
        layout="wide",
        page_icon="🔍",
        initial_sidebar_state="expanded"
    )

    # Custom styling
    st.markdown("""
        <style>
        .main {background-color: #f9f9f9;}
        .stTextArea textarea {min-height: 150px; border-radius: 10px;}
        .stButton>button {border-radius: 8px; padding: 10px 24px;}
        .stExpander {border: 1px solid #e0e0e0; border-radius: 8px;}
        </style>
    """, unsafe_allow_html=True)

    # Header section
    st.title("🔍 Sage-Lens: Agentic AI Research Engine")
    st.markdown("### Your AI-Powered Research Companion")
    st.write("---")

    # Initialize session state
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'current_result' not in st.session_state:
        st.session_state.current_result = None

    # Main input section
    with st.container():
        input_col, btn_col = st.columns([5, 1])
        with input_col:
            topic = st.text_area(
                "📝 Enter Research Topic:",
                placeholder="e.g., Transformer Architecture Optimization",
                help="Describe your topic in detail"
            )
        with btn_col:
            st.write("")
            st.write("")
            if st.button("🚀 Generate", use_container_width=True):
                if topic.strip():
                    with st.spinner("🔬 Agentic AI processors analyzing..."):
                        st.session_state.current_result = SageLensSystem().process_query(topic)
                        # Only add to history if content is a dict (successful generation)
                        if isinstance(st.session_state.current_result["content"], dict):
                            st.session_state.history.append(st.session_state.current_result)
                            st.rerun()

    # Results display
    if st.session_state.current_result:
        result = st.session_state.current_result

        # Check if content is a dict (successful generation) or string (error/empty)
        if isinstance(result["content"], dict) and result["content"].get("content"):
            # Main content columns
            doc_col, ref_col = st.columns([3, 1])

            with doc_col:
                # Documentation display
                with st.expander("📄 Generated Documentation", expanded=True):
                    st.markdown(result["content"]["content"], unsafe_allow_html=True)

                # Generation metrics
                with st.expander("⚙️ Generation Details"):
                    cols = st.columns(2)
                    cols[0].metric("Processing Time", f"{result['content']['latency']:.2f}s")
                    cols[1].metric("AI Engine", result['content']['provider'])
                    st.caption("Powered by Claude-3.5-Sonnet and GPT-4 Turbo")

            with ref_col:
                # Reference materials
                with st.container(border=True):
                    st.subheader("🔗 Curated Resources")

                    # Web results
                    with st.expander("🌐 Web References", expanded=True):
                        if result["references"]["web"]:
                            for i, item in enumerate(result["references"]["web"][:5], 1):
                                st.markdown(f"{i}. [{item['title']}]({item['url']})")
                        else:
                            st.info("No web resources found")

                    # Video results
                    with st.expander("🎥 Video Guides"):
                        if result["references"]["videos"]:
                            for vid in result["references"]["videos"][:3]:
                                st.markdown(f"▶️ [{vid['title']}]({vid['url']})")
                                st.caption(f"Views: {vid.get('views', 'N/A')}")
                        else:
                            st.info("No video guides found")

                # Version history
                with st.expander("🕰 Document Versions"):
                    if len(st.session_state.history) > 1:
                        for i, rev in enumerate(st.session_state.history):
                            if isinstance(rev.get("content"), dict):
                                cols = st.columns([1, 3])
                                cols[0].button(
                                    f"v{i + 1}",
                                    key=f"load_{i}",
                                    on_click=lambda r=rev: st.session_state.update(current_result=r),
                                    help=f"Load version {i + 1}"
                                )
                                cols[1].caption(f"{rev['content']['provider']} | {rev['content']['latency']:.1f}s")
                    else:
                        st.info("No previous versions")
        else:
            # Show error message if content generation failed
            st.error("❌ Failed to generate content. Please check your API keys and try again.")


if __name__ == "__main__":
    main()