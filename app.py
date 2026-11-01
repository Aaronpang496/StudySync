import streamlit as st
import random
import json
import requests

# Set page configuration
st.set_page_config(page_title="StudySync", page_icon="⚡", layout="centered")

# Custom CSS
st.markdown("""
<style>
    .flashcard-container { perspective: 1000px; margin: 20px auto; width: 100%; height: 250px; cursor: pointer; }
    .flashcard { width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.4s ease-in-out; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .flashcard.flipped { transform: rotateY(180deg); }
    .card-side { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: bold; padding: 20px; text-align: center; border-radius: 15px; border: 2px solid #e0e0e0; }
    .card-front { background-color: #ffffff; color: #1e1e1e; }
    .card-back { background-color: #2e5bff; color: #ffffff; transform: rotateY(180deg); }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"term": "Mitosis", "definition": "A type of cell division that results in two daughter cells."},
        {"term": "Photosynthesis", "definition": "The process by which green plants use sunlight to synthesize nutrients."},
        {"term": "Python", "definition": "A high-level, general-purpose programming language."},
    ]

if "active_mode" not in st.session_state: st.session_state.active_mode = "Flashcards"
if "current_index" not in st.session_state: st.session_state.current_index = 0
if "is_flipped" not in st.session_state: st.session_state.is_flipped = False
if "learn_options" not in st.session_state: st.session_state.learn_options = []
if "learn_feedback" not in st.session_state: st.session_state.learn_feedback = None
if "test_submitted" not in st.session_state: st.session_state.test_submitted = False
if "test_answers" not in st.session_state: st.session_state.test_answers = {}

def generate_learn_options():
    if len(st.session_state.flashcards) < 2: return
    current_card = st.session_state.flashcards[st.session_state.current_index]
    wrong_cards = [c for c in st.session_state.flashcards if c["term"] != current_card["term"]]
    pool_size = min(3, len(wrong_cards))
    options = [current_card["definition"]] + [c["definition"] for c in random.sample(wrong_cards, pool_size)]
    random.shuffle(options)
    st.session_state.learn_options = options

if st.session_state.current_index >= len(st.session_state.flashcards):
    st.session_state.current_index = 0

# --- SIDEBAR: AUTOMATED FREE AI GENERATOR ---
with st.sidebar:
    st.subheader("🤖 Free AI Generator")
    
    topic = st.text_input("Topic (e.g., Biology):", placeholder="The Solar System")
    
    # NEW: Optional specific words input
    specific_words = st.text_area(
        "Specific words (Optional):", 
        placeholder="Paste words separated by commas...\ne.g., ATP, Ribosome, Nucleus",
        height=100
    )
    
    if st.button("✨ Generate Deck", type="primary", use_container_width=True):
        if not topic and not specific_words:
            st.warning("Please enter a topic or some specific words.")
        else:
            with st.spinner("AI is generating cards..."):
                try:
                    # Construct the prompt based on user input
                    if specific_words:
                        prompt = f"Create flashcards for these specific terms: {specific_words}. Context/Topic: {topic}. Output ONLY a valid JSON array of objects with 'term' and 'definition' keys. Do not use markdown or any other text."
                    else:
                        prompt = f"Create exactly 5 flashcards about {topic}. Output ONLY a valid JSON array of objects with 'term' and 'definition' keys. Do not use markdown or any other text."
                    
                    # Send request to the free endpoint
                    response = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(prompt)}")
                    
                    if response.status_code == 200:
                        raw_text = response.text.strip()
                        
                        # Clean up formatting if the AI adds markdown
                        if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
                        if raw_text.startswith("```"): raw_text = raw_text[3:-3]
                        
                        # Find the JSON array if the AI added extra text
                        start_idx = raw_text.find('[')
                        end_idx = raw_text.rfind(']')
                        if start_idx != -1 and end_idx != -1:
                            raw_text = raw_text[start_idx:end_idx+1]
                        
                        # Parse the JSON
                        new_cards = json.loads(raw_text)
                        
                        # Update state
                        st.session_state.flashcards = new_cards
                        st.session_state.current_index = 0
                        st.session_state.is_flipped = False
                        st.success(f"Loaded {len(new_cards)} cards!")
                        st.rerun()
                    else:
                        st.error("Free AI server is busy. Try again in a few seconds.")
                        
                except Exception as e:
                    st.error("AI had trouble formatting the response. Please try clicking Generate again.")

    st.divider()
    
    # Manual Importer
    st.subheader("📋 Manual Importer")
    bulk_data = st.text_area("Paste 'Term : Definition' lines here", height=100)
    if st.button("📥 Import Manual Deck", use_container_width=True):
        if bulk_data:
            new_cards = []
            for line in bulk_data.strip().split("\n"):
                if ":" in line:
                    term, definition = line.split(":", 1)
                    new_cards.append({"term": term.strip(), "definition": definition.strip()})
            if new_cards:
                st.session_state.flashcards = new_cards
                st.session_state.current_index = 0
                st.session_state.is_flipped = False
                st.rerun()

    st.write(f"**Deck Status:** {len(st.session_state.flashcards)} cards active.")


# --- MAIN CONTENT ---
st.title("⚡ StudySync Hub")

# Mode Selector
mode = st.radio("Select Mode:", ["Flashcards", "Learn", "Test"], horizontal=True, label_visibility="collapsed")
if mode != st.session_state.active_mode:
    st.session_state.active_mode = mode
    st.session_state.is_flipped = False
    st.session_state.test_submitted = False
    st.rerun()

st.divider()

if len(st.session_state.flashcards) < 3 and st.session_state.active_mode in ["Learn", "Test"]:
    st.warning("⚠️ Please add a collection containing at least 3 cards to unlock full interactive testing suites.")
else:
    current_card = st.session_state.flashcards[st.session_state.current_index]

    if st.session_state.active_mode == "Flashcards":
        st.subheader("📇 Flashcards")
        st.progress((st.session_state.current_index + 1) / len(st.session_state.flashcards))
        
        flipped_class = "flipped" if st.session_state.is_flipped else ""
        st.markdown(f"""
        <div class="flashcard-container">
            <div class="flashcard {flipped_class}">
                <div class="card-side card-front">{current_card['term']}</div>
                <div class="card-side card-back">{current_card['definition']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.current_index = (st.session_state.current_index - 1) % len(st.session_state.flashcards)
                st.session_state.is_flipped = False; st.rerun()
        with col2:
            if st.button("🔄 Flip Card", type="primary", use_container_width=True):
                st.session_state.is_flipped = not st.session_state.is_flipped; st.rerun()
        with col3:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.flashcards)
                st.session_state.is_flipped = False; st.rerun()

    elif st.session_state.active_mode == "Learn":
        st.subheader("🧠 Learn")
        st.write(f"### Select definition for: **{current_card['term']}**")
        
        if not st.session_state.learn_options:
            generate_learn_options()
            
        for opt in st.session_state.learn_options:
            if st.button(opt, use_container_width=True):
                if opt == current_card["definition"]:
                    st.session_state.learn_feedback = ("success", "🎉 Correct!")
                else:
                    st.session_state.learn_feedback = ("error", f"❌ Answer: {current_card['definition']}")
                st.rerun()
        
        if st.session_state.learn_feedback:
            status, text = st.session_state.learn_feedback
            if status == "success": st.success(text)
            else: st.error(text)
            if st.button("Next Card ➡️", type="primary"):
                st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.flashcards)
                st.session_state.learn_feedback = None; generate_learn_options(); st.rerun()

    elif st.session_state.active_mode == "Test":
        st.subheader("📝 Written Test")
        if not st.session_state.test_submitted:
            for idx, card in enumerate(st.session_state.flashcards):
                st.write(f"**Question {idx+1}:** What does **{card['term']}** mean?")
                st.session_state.test_answers[card['term']] = st.text_input("", key=f"q_{idx}", label_visibility="collapsed")
            if st.button("Submit Answers", type="primary", use_container_width=True):
                st.session_state.test_submitted = True
                st.rerun()
        else:
            correct_count = 0
            for card in st.session_state.flashcards:
                u_ans = st.session_state.test_answers.get(card['term'], '').strip().lower()
                t_ans = card['definition'].strip().lower()
                if u_ans and (u_ans in t_ans or t_ans in u_ans):
                    st.success(f"✅ **{card['term']}**\nYour Answer: {st.session_state.test_answers.get(card['term'])}")
                    correct_count += 1
                else:
                    st.error(f"❌ **{card['term']}**\nExpected: {card['definition']}")
            st.metric("Test Accuracy", f"{int((correct_count/len(st.session_state.flashcards))*100)}%")
            
            if st.button("Retake", use_container_width=True):
                st.session_state.test_submitted = False
                st.session_state.test_answers = {}
                st.rerun()
