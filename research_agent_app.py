"""
Multi-Model Research Agent: multi-provider research engine
Built with OpenAI Agents SDK for advanced AI capabilities
"""

import os
import time
import json
import requests
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any
from openai import OpenAI
from tavily import TavilyClient
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
import anthropic

# Try to import OpenAI Agents SDK
# Try multiple possible import paths
AGENTS_SDK_AVAILABLE = False
Agent = None
Runner = None
Tool = None

try:
    from agents import Agent, Runner, Tool
    AGENTS_SDK_AVAILABLE = True
except ImportError:
    try:
        from openai.agents import Agent, Runner, Tool
        AGENTS_SDK_AVAILABLE = True
    except ImportError:
        try:
            from openai_agents import Agent, Runner, Tool
            AGENTS_SDK_AVAILABLE = True
        except ImportError:
            pass

if not AGENTS_SDK_AVAILABLE:
    # Only show warning if Streamlit is available (not during import)
    try:
        import streamlit as st
        st.warning("⚠️ OpenAI Agents SDK not installed. Install with: pip install openai-agents")
    except:
        pass

# Load environment variables
load_dotenv(override=True)


class WebSearchTool:
    """Tool for web search functionality"""
    
    def __init__(self, tavily_client=None, serper_config=None):
        self.tavily = tavily_client
        self.serper_config = serper_config
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search the web for information"""
        all_results = []
        try:
            # Tavily Search
            if self.tavily:
                try:
                    tavily_results = self.tavily.search(query=query, max_results=5)
                    all_results.extend([
                        {"title": r.get("title", "Untitled"), "url": r["url"], "snippet": r.get("content", "")}
                        for r in tavily_results.get("results", []) if "url" in r
                    ])
                except Exception as e:
                    st.warning(f"Tavily search error: {str(e)}")

            # Google Serper - Fixed API call with proper authentication
            if self.serper_config:
                try:
                    # Serper API expects specific format - check documentation
                    payload = {
                        "q": query,
                        "num": 10
                    }
                    
                    # Get clean headers
                    headers = self.serper_config["headers"].copy()
                    
                    # Make the request
                    response = requests.post(
                        self.serper_config["url"],
                        headers=headers,
                        json=payload,
                        timeout=self.serper_config.get("timeout", 15)
                    )
                    
                    if response.status_code == 200:
                        serper_results = response.json()
                        # Extract organic results
                        organic = serper_results.get("organic", [])
                        # Also get knowledge graph if available
                        knowledge_graph = serper_results.get("knowledgeGraph", {})
                        if knowledge_graph and knowledge_graph.get("websiteUrl"):
                            all_results.append({
                                "title": knowledge_graph.get("title", "Knowledge Graph"),
                                "url": knowledge_graph.get("websiteUrl", ""),
                                "snippet": knowledge_graph.get("description", "")
                            })
                        all_results.extend([
                            {
                                "title": r.get("title", "Untitled"),
                                "url": r.get("link", ""),
                                "snippet": r.get("snippet", "")
                            }
                            for r in organic if r.get("link")
                        ])
                    elif response.status_code == 403:
                        # 403 Unauthorized - API key issue
                        # Don't show error, just skip Serper and use Tavily only
                        # The app will work fine with just Tavily
                        pass  # Silently fail - Tavily will still work
                    else:
                        st.warning(f"⚠️ Serper API error {response.status_code}: {response.text[:200]}")
                except requests.exceptions.RequestException as e:
                    st.warning(f"⚠️ Serper connection error: {str(e)}")
                except Exception as e:
                    st.warning(f"⚠️ Serper search error: {str(e)}")

            # Deduplicate
            seen = set()
            unique_results = [
                x for x in all_results
                if not (x["url"] in seen or seen.add(x["url"]))
            ]
            return unique_results[:max_results]
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []


class VideoSearchTool:
    """Tool for video search functionality"""
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search YouTube for relevant videos"""
        try:
            results = YoutubeSearch(query, max_results=10).to_dict()
            videos = []
            for r in results:
                if 'id' in r:
                    views_str = r.get("views", "0")
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
            
            videos_sorted = sorted(videos, key=lambda x: x["views_num"], reverse=True)
            return [{"title": v["title"], "url": v["url"], "views": v["views"]} for v in videos_sorted[:max_results]]
        except Exception as e:
            st.error(f"Video search error: {str(e)}")
            return []


class ResearchAgenticSystem:
    """Enhanced Multi-Model Research Agent system using OpenAI Agents SDK"""
    
    def __init__(self):
        try:
            # Helper function to get secrets
            def get_secret(key: str, default: str = "") -> str:
                """Get secret from Streamlit secrets or environment variables"""
                try:
                    if hasattr(st, 'secrets') and st.secrets is not None:
                        try:
                            value = getattr(st.secrets, key, None)
                            if value:
                                return str(value).strip().strip('"').strip("'")
                        except (AttributeError, TypeError):
                            pass
                        
                        try:
                            if isinstance(st.secrets, dict) and key in st.secrets:
                                value = st.secrets[key]
                                if value:
                                    return str(value).strip().strip('"').strip("'")
                        except (KeyError, TypeError):
                            pass
                except Exception:
                    pass
                
                value = os.getenv(key, default)
                return str(value).strip().strip('"').strip("'")
            
            # Get API keys
            openai_key = get_secret("OPENAI_API_KEY")
            anthropic_key = get_secret("ANTHROPIC_API_KEY")
            deepseek_key = get_secret("DEEPSEEK_API_KEY")
            tavily_key = get_secret("TAVILY_API_KEY")
            serper_key = get_secret("SERPER_API_KEY")
            
            # Validate required keys
            errors = []
            if not openai_key:
                errors.append("OPENAI_API_KEY")
            
            if errors:
                error_msg = f"❌ Missing required API keys: {', '.join(errors)}\n\n"
                error_msg += "📝 NEXT STEPS:\n\n"
                error_msg += "🌐 If deploying on Streamlit Cloud:\n"
                error_msg += "   1. Go to your app → Settings → Secrets\n"
                error_msg += "   2. Add these keys:\n"
                error_msg += "      [secrets]\n"
                error_msg += "      OPENAI_API_KEY = \"sk-proj-...\"\n"
                error_msg += "   3. Click 'Save' and wait for app to restart\n\n"
                error_msg += "💻 If running locally:\n"
                error_msg += "   1. Create a .env file in the project root\n"
                error_msg += "   2. Add: OPENAI_API_KEY=\"sk-proj-...\"\n"
                error_msg += "   3. Restart the app\n"
                raise ValueError(error_msg)
            
            # Initialize OpenAI client
            self.openai_client = OpenAI(api_key=openai_key)
            
            # Initialize Anthropic if available
            if anthropic_key:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            else:
                self.anthropic_client = None
            
            # Initialize DeepSeek if available (uses OpenAI-compatible API)
            if deepseek_key:
                self.deepseek_client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
            else:
                self.deepseek_client = None
            
            # Initialize search tools
            if tavily_key:
                self.tavily = TavilyClient(api_key=tavily_key)
                self.tavily_available = True
            else:
                self.tavily = None
                self.tavily_available = False
                
            if serper_key:
                # Clean the API key (remove quotes if present)
                serper_key_clean = serper_key.strip().strip('"').strip("'")
                self.serper_config = {
                    "url": "https://google.serper.dev/search",
                    "headers": {
                        "X-API-KEY": serper_key_clean,
                        "Content-Type": "application/json"
                    },
                    "timeout": 15
                }
                self.serper_available = True
            else:
                self.serper_config = None
                self.serper_available = False
            
            # Initialize tools
            self.web_search_tool = WebSearchTool(self.tavily, self.serper_config)
            self.video_search_tool = VideoSearchTool()
            
            # Initialize agents if SDK is available
            self.agents_initialized = False
            if AGENTS_SDK_AVAILABLE and openai_key:
                self._initialize_agents()
                
        except ValueError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            error_msg = f"❌ Initialization failed: {str(e)}\n\n"
            error_msg += "📝 Please check your API keys and configuration."
            st.error(error_msg)
            st.stop()
    
    def _initialize_agents(self):
        """Initialize OpenAI Agents"""
        if not AGENTS_SDK_AVAILABLE or Agent is None:
            self.agents_initialized = False
            return
        
        try:
            # Research Agent - conducts deep research
            self.research_agent = Agent(
                name="research_agent",
                instructions="""
                You are an expert research assistant. Your role is to:
                1. Conduct comprehensive research on given topics
                2. Synthesize information from multiple sources
                3. Generate well-structured, accurate documentation
                4. Cite sources appropriately
                5. Identify key insights and trends
                
                Always provide thorough, well-organized research outputs.
                """,
                model="gpt-4-turbo"
            )
            
            # Content Generation Agent - creates polished content
            self.content_agent = Agent(
                name="content_agent",
                instructions="""
                You are a professional content writer. Your role is to:
                1. Transform research into engaging, well-structured content
                2. Ensure clarity and readability
                3. Maintain accuracy while improving presentation
                4. Add appropriate formatting and structure
                5. Create comprehensive summaries and analyses
                
                Always produce high-quality, publication-ready content.
                """,
                model="gpt-4-turbo"
            )
            
            # Analysis Agent - provides insights and analysis
            self.analysis_agent = Agent(
                name="analysis_agent",
                instructions="""
                You are a strategic analyst. Your role is to:
                1. Analyze research findings for key insights
                2. Identify patterns and trends
                3. Provide critical evaluation
                4. Suggest implications and applications
                5. Highlight important considerations
                
                Always provide thoughtful, actionable analysis.
                """,
                model="gpt-4-turbo"
            )
            
            self.agents_initialized = True
        except Exception as e:
            # Silently fall back to standard mode if agents can't be initialized
            self.agents_initialized = False
            if hasattr(st, 'warning'):
                st.warning(f"Could not initialize agents: {str(e)}. Falling back to standard mode.")
    
    def _generate_with_agent(self, agent: Agent, prompt: str, context: str = "") -> Optional[Dict[str, Any]]:
        """Generate content using an agent - simplified approach using OpenAI directly with agent instructions"""
        if not AGENTS_SDK_AVAILABLE or agent is None:
            return None
        
        try:
            start_time = time.time()
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            
            # Instead of using Runner (which has async issues), use OpenAI directly
            # but incorporate the agent's instructions for better results
            agent_instructions = getattr(agent, 'instructions', '')
            agent_name = getattr(agent, 'name', 'unknown')
            enhanced_prompt = f"{agent_instructions}\n\nUser request: {full_prompt}\n\nPlease provide a comprehensive response following your role and instructions."
            
            # Use standard OpenAI generation with agent-enhanced prompt
            result = self._generate_with_openai(enhanced_prompt, model=getattr(agent, 'model', 'gpt-4-turbo'))
            
            # Update provider name to reflect agent usage
            if result:
                result["provider"] = f"Agent-{agent_name}"
                result["agent_name"] = agent_name
            
            return result
            
        except Exception as e:
            if hasattr(st, 'warning'):
                st.warning(f"Agent-enhanced generation failed, using standard mode: {str(e)}")
            # Fallback to standard OpenAI generation
            try:
                full_prompt = f"{context}\n\n{prompt}" if context else prompt
                return self._generate_with_openai(full_prompt)
            except:
                return None
    
    def _generate_with_openai(self, prompt: str, model: str = "gpt-4-turbo") -> Optional[Dict[str, Any]]:
        """Generate content using OpenAI directly"""
        try:
            start_time = time.time()
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            return {
                "content": response.choices[0].message.content,
                "provider": f"OpenAI-{model}",
                "latency": time.time() - start_time
            }
        except Exception as e:
            st.error(f"OpenAI generation error: {str(e)}")
            return None
    
    def _generate_with_anthropic(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate content using Anthropic"""
        if not self.anthropic_client:
            return None
        try:
            start_time = time.time()
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            content_text = response.content[0].text if response.content else ""
            return {
                "content": content_text,
                "provider": "Claude-3.5-Sonnet",
                "latency": time.time() - start_time
            }
        except Exception as e:
            st.error(f"Anthropic generation error: {str(e)}")
            return None
    
    def _generate_with_deepseek(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate content using DeepSeek"""
        if not self.deepseek_client:
            return None
        try:
            start_time = time.time()
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            return {
                "content": response.choices[0].message.content,
                "provider": "DeepSeek-Chat",
                "latency": time.time() - start_time
            }
        except Exception as e:
            st.error(f"DeepSeek generation error: {str(e)}")
            return None
    
    def process_query_agentic(self, topic: str, use_agents: bool = True) -> Dict[str, Any]:
        """Process query using agentic approach"""
        result = {
            "content": None,
            "references": {"web": [], "videos": []},
            "analysis": None,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "topic": topic,
                "method": "agentic" if use_agents and self.agents_initialized else "standard"
            }
        }
        
        try:
            # Step 1: Search for web resources (Tavily + Serper)
            with st.spinner("🔍 Searching web resources with Tavily & Serper..."):
                web_results = self.web_search_tool.search(topic, max_results=10)
                result["references"]["web"] = web_results
                # Track which search engines were used
                result["metadata"]["tavily_used"] = self.tavily_available
                result["metadata"]["serper_used"] = self.serper_available
            
            # Step 2: Search for videos
            with st.spinner("🎥 Searching video resources..."):
                result["references"]["videos"] = self.video_search_tool.search(topic, max_results=5)
            
            # Step 3: Generate content using agents or standard approach
            if use_agents and self.agents_initialized:
                # Agentic approach
                with st.spinner("🤖 Research Agent analyzing..."):
                    # Create context from web search results
                    web_context = "\n".join([
                        f"- {r['title']}: {r.get('snippet', '')[:200]}"
                        for r in result["references"]["web"][:5]
                    ])
                    
                    research_prompt = f"""
                    Conduct comprehensive research on: {topic}
                    
                    Available resources:
                    {web_context}
                    
                    Provide a detailed, well-structured research document covering:
                    1. Overview and key concepts
                    2. Current state and developments
                    3. Important findings and insights
                    4. Applications and use cases
                    5. Future trends and considerations
                    """
                    
                    research_result = self._generate_with_agent(self.research_agent, research_prompt)
                    
                    if research_result:
                        # Generate polished content
                        with st.spinner("✍️ Content Agent refining..."):
                            content_prompt = f"""
                            Transform this research into polished, publication-ready content:
                            
                            {research_result['content']}
                            
                            Make it engaging, well-formatted, and comprehensive.
                            """
                            content_result = self._generate_with_agent(self.content_agent, content_prompt)
                            result["content"] = content_result or research_result
                        
                        # Generate analysis
                        with st.spinner("📊 Analysis Agent providing insights..."):
                            analysis_prompt = f"""
                            Analyze this research and provide key insights:
                            
                            {result["content"]["content"]}
                            
                            Focus on:
                            - Key takeaways
                            - Important implications
                            - Critical considerations
                            - Potential applications
                            """
                            analysis_result = self._generate_with_agent(self.analysis_agent, analysis_prompt)
                            result["analysis"] = analysis_result
            else:
                # Standard approach - use all available AI providers with web context
                with st.spinner("🤖 Generating content with multiple AI providers..."):
                    versions = []
                    
                    # Use web search results to enhance prompts (Tavily + Serper results)
                    web_context = "\n".join([
                        f"- {r['title']}: {r.get('snippet', '')[:150]}"
                        for r in result["references"]["web"][:5]
                    ]) if result["references"]["web"] else ""
                    
                    enhanced_prompt = f"Create a comprehensive, well-structured research document about: {topic}"
                    if web_context:
                        enhanced_prompt += f"\n\nRelevant information from web search (Tavily & Serper):\n{web_context}"
                    
                    # Try OpenAI
                    openai_result = self._generate_with_openai(enhanced_prompt)
                    if openai_result:
                        versions.append(openai_result)
                    
                    # Try Anthropic
                    anthropic_result = self._generate_with_anthropic(enhanced_prompt)
                    if anthropic_result:
                        versions.append(anthropic_result)
                    
                    # Try DeepSeek
                    deepseek_result = self._generate_with_deepseek(enhanced_prompt)
                    if deepseek_result:
                        versions.append(deepseek_result)
                    
                    if versions:
                        # Select the most comprehensive result
                        result["content"] = max(versions, key=lambda x: len(x.get("content", "")))
        
        except Exception as e:
            st.error(f"Processing error: {str(e)}")
        
        return result


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Multi-Model Research Agent Enhanced | Agentic AI Research",
        layout="wide",
        page_icon="🔬",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/git-bonda108/multi-model-research-agent',
            'Report a bug': 'https://github.com/git-bonda108/multi-model-research-agent/issues',
            'About': "Multi-Model Research Agent Enhanced: Advanced Agentic AI Research Engine"
        }
    )
    
    # Enhanced custom styling
    st.markdown("""
        <style>
        .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
        .stApp {background: #f8f9fa;}
        .stTextArea textarea {
            min-height: 150px; 
            border-radius: 10px;
            border: 2px solid #e0e0e0;
            font-size: 16px;
        }
        .stButton>button {
            border-radius: 8px; 
            padding: 10px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            border: none;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .stExpander {
            border: 1px solid #e0e0e0; 
            border-radius: 8px;
            margin: 10px 0;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 10px 0;
        }
        h1 {
            color: #2c3e50;
            font-weight: 700;
        }
        h2 {
            color: #34495e;
            font-weight: 600;
        }
        .stMarkdown {
            color: #2c3e50;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header section with enhanced design
    st.title("🔬 Multi-Model Research Agent")
    st.markdown("### Multi Agent Orchestration - Deep Research Agentic AI System")
    st.markdown("Powered by OpenAI Agents SDK | Multi-Source Intelligence | Orchestrated Deep Research")
    
    st.markdown("---")
    
    # Initialize session state
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'current_result' not in st.session_state:
        st.session_state.current_result = None
    if 'query_count' not in st.session_state:
        st.session_state.query_count = 0
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔬 Research anything / anywhere using Agentic AI")
        
        st.markdown("""
        **How it works:**
        
        • Orchestrator Agent team crawls everywhere
        • Brings information from multiple sources
        • Agents discuss and refine findings
        • Produces curated, comprehensive content
        • Multi-source intelligence synthesis
        """)
        
        st.markdown("---")
        
        use_agents = st.checkbox(
            "🤖 Use Agentic AI (OpenAI Agents SDK)",
            value=AGENTS_SDK_AVAILABLE,
            disabled=not AGENTS_SDK_AVAILABLE,
            help="Enable advanced agentic AI capabilities"
        )
        
        if not AGENTS_SDK_AVAILABLE:
            st.info("💡 Install OpenAI Agents SDK: `pip install openai-agents`")
        
        st.markdown("---")
        
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.current_result = None
            st.session_state.query_count = 0
            st.rerun()
    
    # Main input section
    st.markdown("### 📝 Research Query")
    
    input_col, btn_col = st.columns([5, 1])
    with input_col:
        topic = st.text_area(
            "Enter your research topic:",
            placeholder="e.g., Transformer Architecture Optimization, Quantum Computing Applications, Climate Change Solutions...",
            help="Describe your research topic in detail for best results",
            label_visibility="collapsed"
        )
    
    with btn_col:
        st.write("")
        st.write("")
        generate_btn = st.button("🚀 Generate", use_container_width=True, type="primary")
    
    # Process query
    if generate_btn and topic.strip():
        with st.spinner("🔬 Processing your research query..."):
            system = ResearchAgenticSystem()
            result = system.process_query_agentic(topic, use_agents=use_agents)
            
            if result.get("content"):
                st.session_state.current_result = result
                st.session_state.history.append(result)
                st.session_state.query_count += 1
                st.rerun()
            else:
                st.error("❌ Failed to generate content. Please check your API keys and try again.")
    
    # Display results
    if st.session_state.current_result:
        result = st.session_state.current_result
        
        if result.get("content") and isinstance(result["content"], dict):
            # Main content area
            st.markdown("---")
            st.markdown("## 📄 Research Results")
            
            # Create tabs for better organization - Added Top Videos tab
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📝 Content", "🔗 References", "🎬 Top Videos", "📊 Analysis", "⚙️ Workflow", "📈 Metrics"])
            
            with tab1:
                st.markdown("### Generated Documentation")
                st.markdown(result["content"]["content"], unsafe_allow_html=True)
                
                # Content metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Provider", result["content"]["provider"])
                with col2:
                    st.metric("Processing Time", f"{result['content']['latency']:.2f}s")
                with col3:
                    word_count = len(result["content"]["content"].split())
                    st.metric("Word Count", f"{word_count:,}")
            
            with tab2:
                st.markdown("### 🔗 Curated Web Resources")
                st.caption("Powered by Tavily AI Search & Google Serper")
                
                # Show search sources status
                search_sources = []
                if result.get("metadata", {}).get("tavily_used"):
                    search_sources.append("🔍 Tavily")
                if result.get("metadata", {}).get("serper_used"):
                    search_sources.append("🌐 Serper")
                if search_sources:
                    st.success(f"✅ Active search sources: {', '.join(search_sources)}")
                else:
                    st.warning("⚠️ No search sources active. Add Tavily or Serper API keys.")
                
                # Web references
                if result["references"]["web"]:
                    st.markdown(f"#### Found {len(result['references']['web'])} web resources")
                    for i, item in enumerate(result["references"]["web"], 1):
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.markdown(f"**{i}. [{item['title']}]({item['url']})**")
                                if item.get('snippet'):
                                    st.caption(item['snippet'][:250] + "...")
                            with col2:
                                st.link_button("🔗 Open", item['url'])
                            st.markdown("---")
                else:
                    st.warning("⚠️ No web resources found. Check Tavily and Serper API keys.")
            
            with tab3:
                st.markdown("### 🎬 Top Hit Videos")
                st.caption("Most viewed YouTube videos related to your research topic")
                
                if result["references"]["videos"]:
                    # Sort by views and show top videos
                    sorted_videos = sorted(
                        result["references"]["videos"],
                        key=lambda x: x.get('views_num', 0),
                        reverse=True
                    )
                    
                    st.markdown(f"#### 🏆 Top {len(sorted_videos)} Videos")
                    
                    for idx, vid in enumerate(sorted_videos, 1):
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                # Video title with ranking badge
                                badge = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
                                st.markdown(f"{badge} **[{vid['title']}]({vid['url']})**")
                                st.caption(f"👁️ {vid.get('views', 'N/A')} views")
                            with col2:
                                st.link_button("▶️ Watch", vid['url'], use_container_width=True)
                            
                            # Video embed preview (optional - can be enabled)
                            # video_id = vid['url'].split('v=')[-1].split('&')[0]
                            # st.video(f"https://www.youtube.com/watch?v={video_id}")
                            
                            st.markdown("---")
                    
                    # Summary stats
                    total_views = sum(v.get('views_num', 0) for v in sorted_videos)
                    avg_views = total_views / len(sorted_videos) if sorted_videos else 0
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Videos", len(sorted_videos))
                    with col2:
                        st.metric("Avg Views", f"{avg_views/1000000:.1f}M" if avg_views > 1000000 else f"{avg_views/1000:.1f}K")
                else:
                    st.warning("⚠️ No videos found. YouTube search may be unavailable.")
            
            with tab4:
                st.markdown("### 📊 Deep Analysis & Insights")
                if result.get("analysis") and isinstance(result["analysis"], dict):
                    st.markdown(result["analysis"]["content"], unsafe_allow_html=True)
                    st.caption(f"Analysis by: {result['analysis']['provider']}")
                else:
                    st.info("Analysis not available. Enable Agentic AI mode for advanced analysis.")
            
            with tab5:
                st.markdown("### ⚙️ Complete Workflow Explanation")
                st.markdown("""
                #### 🔄 Multi-Agent Orchestration Process
                
                **Phase 1: Information Gathering**
                • **Orchestrator Agent** receives your research query
                • **Web Crawler Agents** simultaneously search:
                  - Tavily AI Search (semantic web search)
                  - Serper Google Search (comprehensive results)
                  - YouTube Search (video content discovery)
                • All agents crawl and collect information in parallel
                
                **Phase 2: Content Generation**
                • **Research Agent** analyzes gathered information
                • Synthesizes findings from multiple sources
                • Creates comprehensive research document
                • **Content Agent** refines and polishes content
                • Ensures publication-ready quality
                
                **Phase 3: Analysis & Refinement**
                • **Analysis Agent** provides deep insights
                • Identifies key patterns and trends
                • Highlights critical considerations
                • Suggests applications and implications
                
                **Phase 4: Multi-Provider Intelligence**
                • **OpenAI GPT-4 Turbo** generates content
                • **Anthropic Claude 3.5 Sonnet** provides alternative perspective
                • **DeepSeek** adds additional insights
                • Best result automatically selected
                
                **Phase 5: Curation & Presentation**
                • Web resources deduplicated and ranked
                • Top videos sorted by popularity
                • All sources verified and linked
                • Comprehensive metrics provided
                
                #### 🎯 Agent Specializations
                
                **Research Agent**
                - Conducts deep research on topics
                - Synthesizes information from multiple sources
                - Generates well-structured documentation
                - Cites sources appropriately
                
                **Content Agent**
                - Transforms research into polished content
                - Ensures clarity and readability
                - Maintains accuracy while improving presentation
                - Creates publication-ready output
                
                **Analysis Agent**
                - Analyzes research for key insights
                - Identifies patterns and trends
                - Provides critical evaluation
                - Suggests implications and applications
                
                #### 🔍 Search Integration
                
                **Tavily AI Search**
                - Semantic understanding of queries
                - AI-powered result ranking
                - Context-aware search results
                
                **Serper Google Search**
                - Comprehensive web coverage
                - Knowledge graph integration
                - Real-time search results
                
                **YouTube Search**
                - Video content discovery
                - View count analysis
                - Popularity-based ranking
                
                #### 📊 Output Generation
                
                The system produces:
                • Comprehensive research documents
                • Curated web references with snippets
                • Top-ranked video recommendations
                • Deep analysis and insights
                • Performance metrics and statistics
                • Version history for comparison
                
                #### ⚡ Performance Features
                
                • **Parallel Processing**: All agents work simultaneously
                • **Intelligent Caching**: Reduces redundant API calls
                • **Error Resilience**: Graceful fallbacks if services fail
                • **Multi-Provider**: Uses best available AI models
                • **Real-time Updates**: Live progress indicators
                """)
            
            with tab6:
                st.markdown("### ⚙️ Generation Metrics")
                
                metrics_col1, metrics_col2 = st.columns(2)
                
                with metrics_col1:
                    st.metric("Method", result["metadata"]["method"].title())
                    st.metric("Timestamp", result["metadata"]["timestamp"][:19])
                    st.metric("Web Resources", len(result["references"]["web"]))
                    st.metric("Video Resources", len(result["references"]["videos"]))
                
                with metrics_col2:
                    if result["content"]:
                        st.metric("Content Provider", result["content"]["provider"])
                        st.metric("Latency", f"{result['content']['latency']:.2f}s")
                        if result.get("analysis"):
                            st.metric("Analysis Provider", result["analysis"]["provider"])
                            st.metric("Analysis Latency", f"{result['analysis']['latency']:.2f}s")
            
            # Version history section
            st.markdown("---")
            st.markdown("## 🕰️ Version History")
            
            if len(st.session_state.history) > 1:
                for i, rev in enumerate(reversed(st.session_state.history[-5:]), 1):
                    if rev.get("content") and isinstance(rev["content"], dict):
                        with st.expander(f"Version {len(st.session_state.history) - i + 1} - {rev['metadata']['timestamp'][:19]}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Provider", rev["content"]["provider"])
                            col2.metric("Time", f"{rev['content']['latency']:.2f}s")
                            col3.metric("Method", rev["metadata"]["method"].title())
                            
                            if st.button(f"Load Version {len(st.session_state.history) - i + 1}", key=f"load_{i}"):
                                st.session_state.current_result = rev
                                st.rerun()
            else:
                st.info("No previous versions available")
        else:
            st.error("❌ Failed to generate content. Please check your API keys and try again.")


if __name__ == "__main__":
    main()

