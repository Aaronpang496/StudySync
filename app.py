import streamlit as st
import random
import json
import requests
import time

st.set_page_config(page_title="StudySync", page_icon="🎮", layout="centered", initial_sidebar_state="expanded")

# --- FUN CSS & ANIMATIONS ---
st.markdown("""
<style>
    /* Global Font */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }
    
    /* Flashcard 3D Bounce */
    .flashcard-container { perspective: 1000px; margin: 30px auto; width: 100%; height: 250px; cursor: pointer; }
    .flashcard { width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); }
    .flashcard.flipped { transform: rotateY(180deg); }
    .card-side { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 900; padding: 30px; text-align: center; border-radius: 20px; border: 4px solid #ffffff; }
    .card-front { background: linear-gradient(135deg, #ffffff, #f0f4ff); color: #1e1e1e; }
    .card-back { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #ffffff; transform: rotateY(180deg); }
    
    /* Fun Buttons */
    .stButton>button { border-radius: 12px; font-weight: 700; transition: all 0.2s; border: none; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    
    /* XP Badge */
    .xp-badge { background: #ffd700; color: #000; padding: 10px; border-radius: 10px; text-align: center; font-weight: 900; font-size: 20px; border: 3px solid #ffaa00; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- AUDIO TRICK (Plays sound without external files) ---
def play_sound(sound_type):
    if sound_type == "correct":
        audio_html = """<audio autoplay="true" src="https://assets.mixkit.co/active_storage/sfx/2000/2000-preview.mp3"></audio>"""
    else:
        audio_html = """<audio autoplay="true" src="https://assets.mixkit.co/active_storage/sfx/2003/2003-preview.mp3"></audio>"""
    st.markdown(audio_html, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"term": "Mitosis", "definition": "A type of cell division that results in two daughter cells."},
        {"term": "Photosynthesis", "definition": "The process by which green plants use sunlight to synthesize nutrients."},
        {"term": "Python", "definition": "A high-level, general-purpose programming language."},
        {"term": "Atom", "definition": "The basic unit of a chemical element."},
        {"term": "Gravity", "definition": "The force that attracts a body toward the center of the earth."},
    ]

if "active_mode" not in st.session_state: st.session_state.active_mode = "Flashcards"
if "current_index" not in st.session_state: st.session_state.current_index = 0
if "is_flipped" not in st.session_state: st.session_state.is_flipped = False
if "learn_options" not in st.session_state: st.session_state.learn_options = []
if "learn_feedback" not in st.session_state: st.session_state.learn_feedback = None
if "test_submitted" not in st.session_state: st.session_state.test_submitted = False
if "test_answers" not in st.session_state: st.session_state.test_answers = {}

# Match Game State
if "match_selected_term" not in st.session_state: st.session_state.match_selected_term = None
if "match_matched" not in st.session_state: st.session_state.match_matched = []
if "match_start_time" not in st.session_state: st.session_state.match_start_time = None
if "match_moves" not in st.session_state: st.session_state.match_moves = 0

# Scramble Game State
if "scramble_card" not in st.session_state: st.session_state.scramble_card = None
if "scramble_letters" not in st.session_state: st.session_state.scramble_letters = []
if "scramble_answer" not in st.session_state: st.session_state.scramble_answer = ""

# True/False Game State
if "tf_score" not in st.session_state: st.session_state.tf_score = 0
if "tf_playing" not in st.session_state: st.session_state.tf_playing = False
if "tf_current" not in st.session_state: st.session_state.tf_current = None
if "tf_is_correct" not in st.session_state: st.session_state.tf_is_correct = True

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

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f'<div class="xp-badge">🏆 {st.session_state.xp} XP</div>', unsafe_allow_html=True)
    
    st.subheader("🤖 AI Deck Generator")
    topic = st.text_input("Topic:", placeholder="e.g., Space, Biology")
    specific_words = st.text_area("Specific words (Optional):", placeholder="ATP, Ribosome", height=80)
    
    if st.button("✨ Generate Deck", type="primary", use_container_width=True):
        if not topic and not specific_words:
            st.warning("Enter a topic or words.")
        else:
            with st.spinner("AI is cooking up your cards..."):
                try:
                    if specific_words:
                        prompt = f"Create flashcards for these terms: {specific_words}. Context: {topic}. Output ONLY a valid JSON array of objects with 'term' and 'definition' keys. No markdown."
                    else:
                        prompt = f"Create exactly 5 flashcards about {topic}. Output ONLY a valid JSON array of objects with 'term' and 'definition' keys. No markdown."
                    
                    response = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(prompt)}")
                    if response.status_code == 200:
                        raw_text = response.text.strip()
                        if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
                        start_idx = raw_text.find('[')
                        end_idx = raw_text.rfind(']')
                        if start_idx != -1 and end_idx != -1: raw_text = raw_text[start_idx:end_idx+1]
                        
                        new_cards = json.loads(raw_text)
                        st.session_state.flashcards = new_cards
                        st.session_state.current_index = 0
                        st.success(f"Loaded {len(new_cards)} cards!")
                        st.rerun()
                    else:
                        st.error("Server busy. Try again.")
                except Exception as e:
                    st.error("Error parsing AI response. Try clicking Generate again.")
    
    st.divider()
    st.caption(f"Deck Status: **{len(st.session_state.flashcards)}** active cards.")

# --- MAIN UI ---
st.title("⚡ StudySync Arcade")

modes = ["Flashcards", "Learn", "Test", "Match Game", "Scramble", "True/False"]
mode = st.radio("Select Mode:", modes, horizontal=True, label_visibility="collapsed")

if mode != st.session_state.active_mode:
    st.session_state.active_mode = mode
    st.session_state.is_flipped = False
    st.session_state.test_submitted = False
    st.session_state.match_start_time = None
    st.session_state.scramble_card = None
    st.session_state.tf_playing = False
    st.rerun()

st.divider()

if len(st.session_state.flashcards) < 4 and st.session_state.active_mode in ["Learn", "Test", "Match Game", "True/False"]:
    st.warning("⚠️ You need at least 4 cards to play this mode.")
else:
    current_card = st.session_state.flashcards[st.session_state.current_index]

    # 1. FLASHCARDS
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
        if col1.button("⬅️ Prev", use_container_width=True):
            st.session_state.current_index = (st.session_state.current_index - 1) % len(st.session_state.flashcards)
            st.session_state.is_flipped = False; st.rerun()
        if col2.button("🔄 Flip", type="primary", use_container_width=True):
            st.session_state.is_flipped = not st.session_state.is_flipped; st.rerun()
        if col3.button("Next ➡️", use_container_width=True):
            st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.flashcards)
            st.session_state.is_flipped = False; st.rerun()

    # 2. LEARN
    elif st.session_state.active_mode == "Learn":
        st.subheader("🧠 Learn")
        st.write(f"### Definition of: **{current_card['term']}**")
        if not st.session_state.learn_options: generate_learn_options()
        
        for opt in st.session_state.learn_options:
            if st.button(opt, use_container_width=True, disabled=st.session_state.learn_feedback is not None):
                if opt == current_card["definition"]: 
                    st.session_state.learn_feedback = ("success", "🎉 Correct! +10 XP")
                    st.session_state.xp += 10
                    play_sound("correct")
                else: 
                    st.session_state.learn_feedback = ("error", f"❌ Oops! The answer was: {current_card['definition']}")
                    play_sound("wrong")
                st.rerun()
                
        if st.session_state.learn_feedback:
            status, text = st.session_state.learn_feedback
            if status == "success": 
                st.success(text)
                st.balloons()
            else: 
                st.error(text)
                
            if st.button("Next Card ➡️", type="primary"):
                st.session_state.current_index = (st.session_state.current_index + 1) % len(st.session_state.flashcards)
                st.session_state.learn_feedback = None; generate_learn_options(); st.rerun()

    # 3. TEST
    elif st.session_state.active_mode == "Test":
        st.subheader("📝 Boss Fight (Test)")
        if not st.session_state.test_submitted:
            for idx, card in enumerate(st.session_state.flashcards):
                st.write(f"**Q{idx+1}:** What does **{card['term']}** mean?")
                st.session_state.test_answers[card['term']] = st.text_input("", key=f"q_{idx}", label_visibility="collapsed")
            if st.button("Submit Answers", type="primary"):
                st.session_state.test_submitted = True; st.rerun()
        else:
            correct_count = 0
            for card in st.session_state.flashcards:
                u_ans = st.session_state.test_answers.get(card['term'], '').strip().lower()
                t_ans = card['definition'].strip().lower()
                if u_ans and (u_ans in t_ans or t_ans in u_ans):
                    st.success(f"✅ **{card['term']}**: {st.session_state.test_answers.get(card['term'])}")
                    correct_count += 1
                else: st.error(f"❌ **{card['term']}** (Expected: {card['definition']})")
            
            acc = int((correct_count/len(st.session_state.flashcards))*100)
            st.metric("Accuracy", f"{acc}%")
            st.session_state.xp += (acc // 2) # Give XP based on accuracy
            
            if st.button("Retake"): st.session_state.test_submitted = False; st.session_state.test_answers = {}; st.rerun()

    # 4. MATCH GAME
    elif st.session_state.active_mode == "Match Game":
        st.subheader("🎮 Match Game")
        
        if st.session_state.match_start_time is None:
            st.session_state.match_start_time = time.time()
            st.session_state.match_matched = []
            st.session_state.match_selected_term = None
            st.session_state.match_moves = 0
            game_cards = random.sample(st.session_state.flashcards, min(6, len(st.session_state.flashcards)))
            st.session_state.match_game_cards = game_cards
            
        if len(st.session_state.match_matched) == len(st.session_state.match_game_cards):
            elapsed = round(time.time() - st.session_state.match_start_time, 1)
            st.success(f"🎉 Victory! Matched in {elapsed} seconds with {st.session_state.match_moves} moves!")
            st.balloons()
            if st.button("Play Again"):
                st.session_state.match_start_time = None; st.rerun()
        else:
            elapsed = round(time.time() - st.session_state.match_start_time, 1)
            st.write(f"⏱️ Time: **{elapsed}s** | 🔀 Moves: **{st.session_state.match_moves}**")
            
            terms = [c["term"] for c in st.session_state.match_game_cards if c["term"] not in st.session_state.match_matched]
            defs = [c["definition"] for c in st.session_state.match_game_cards if c["definition"] not in st.session_state.match_matched]
            random.shuffle(terms)
            random.shuffle(defs)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Terms**")
                for t in terms:
                    if st.button(t, key=f"term_{t}", use_container_width=True, type="primary" if st.session_state.match_selected_term == t else "secondary"):
                        st.session_state.match_selected_term = t
                        st.rerun()
            with col2:
                st.write("**Definitions**")
                for d in defs:
                    if st.button(d, key=f"def_{d}", use_container_width=True):
                        if st.session_state.match_selected_term:
                            st.session_state.match_moves += 1
                            correct_def = next(c["definition"] for c in st.session_state.match_game_cards if c["term"] == st.session_state.match_selected_term)
                            if d == correct_def:
                                st.session_state.match_matched.append(st.session_state.match_selected_term)
                                st.session_state.match_selected_term = None
                                play_sound("correct")
                            else:
                                st.session_state.match_selected_term = None
                                play_sound("wrong")
                            st.rerun()

    # 5. SCRAMBLE GAME
    elif st.session_state.active_mode == "Scramble":
        st.subheader("🧩 Scramble")
        
        if st.session_state.scramble_card is None:
            st.session_state.scramble_card = random.choice(st.session_state.flashcards)
            word = st.session_state.scramble_card["term"].replace(" ", "") 
            letters = list(word.upper())
            random.shuffle(letters)
            st.session_state.scramble_letters = letters
            st.session_state.scramble_answer = ""
            st.rerun()

        st.info(f"**Clue:** {st.session_state.scramble_card['definition']}")
        st.write(f"### {st.session_state.scramble_answer if st.session_state.scramble_answer else '_ _ _'}")
        
        cols = st.columns(6)
        for i, letter in enumerate(st.session_state.scramble_letters):
            if cols[i % 6].button(letter, key=f"letter_{i}", use_container_width=True):
                st.session_state.scramble_answer += letter
                st.session_state.scramble_letters.pop(i)
                st.rerun()
                
        if st.button("🔄 Reset Word", use_container_width=True):
            st.session_state.scramble_card = None; st.rerun()
            
        if st.session_state.scramble_answer == st.session_state.scramble_card["term"].replace(" ", "").upper():
            st.success("🎉 Unscrambled!")
            play_sound("correct")
            st.session_state.xp += 15
            if st.button("Next Word ➡️", type="primary"):
                st.session_state.scramble_card = None; st.rerun()
        elif len(st.session_state.scramble_letters) == 0:
            st.error(f"❌ It was **{st.session_state.scramble_card['term']}**.")
            play_sound("wrong")
            if st.button("Try Again ➡️", type="primary"):
                st.session_state.scramble_card = None; st.rerun()

    # 6. TRUE / FALSE GAME
    elif st.session_state.active_mode == "True/False":
        st.subheader("⚖️ True or False (Survival)")
        
        if not st.session_state.tf_playing:
            st.write("🏆 **High Score:** " + str(st.session_state.tf_score))
            if st.button("▶️ Start Survival Mode", type="primary"):
                st.session_state.tf_playing = True
                st.session_state.tf_score = 0
                st.session_state.tf_current = random.choice(st.session_state.flashcards)
                st.session_state.tf_is_correct = random.choice([True, False])
                st.rerun()
        else:
            st.write(f"🔥 **Streak:** {st.session_state.tf_score}")
            
            shown_def = st.session_state.tf_current["definition"]
            if not st.session_state.tf_is_correct:
                wrong_cards = [c for c in st.session_state.flashcards if c["term"] != st.session_state.tf_current["term"]]
                if wrong_cards:
                    shown_def = random.choice(wrong_cards)["definition"]
            
            st.markdown(f"### {st.session_state.tf_current['term']}")
            st.info(f"*{shown_def}*")
            
            col1, col2 = st.columns(2)
            if col1.button("✅ TRUE", use_container_width=True, type="primary"):
                if st.session_state.tf_is_correct:
                    st.session_state.tf_score += 1
                    st.session_state.xp += 5
                    play_sound("correct")
                    st.session_state.tf_current = random.choice(st.session_state.flashcards)
                    st.session_state.tf_is_correct = random.choice([True, False])
                    st.rerun()
                else:
                    st.error("❌ Game Over! That was False.")
                    play_sound("wrong")
                    st.session_state.tf_playing = False
                    st.rerun()
                    
            if col2.button("❌ FALSE", use_container_width=True, type="secondary"):
                if not st.session_state.tf_is_correct:
                    st.session_state.tf_score += 1
                    st.session_state.xp += 5
                    play_sound("correct")
                    st.session_state.tf_current = random.choice(st.session_state.flashcards)
                    st.session_state.tf_is_correct = random.choice([True, False])
                    st.rerun()
                else:
                    st.error("❌ Game Over! That was True.")
                    play_sound("wrong")
                    st.session_state.tf_playing = False
                    st.rerun()
