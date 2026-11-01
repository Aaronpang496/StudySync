import streamlit as st
import random
import json
import requests
import time

st.set_page_config(page_title="StudySync", page_icon="🎮", layout="centered")

# --- FUN CSS & ANIMATIONS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }
    .flashcard-container { perspective: 1000px; margin: 30px auto; width: 100%; height: 250px; cursor: pointer; }
    .flashcard { width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); }
    .flashcard.flipped { transform: rotateY(180deg); }
    .card-side { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 900; padding: 30px; text-align: center; border-radius: 20px; border: 4px solid #ffffff; }
    .card-front { background: linear-gradient(135deg, #ffffff, #f0f4ff); color: #1e1e1e; }
    .card-back { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #ffffff; transform: rotateY(180deg); }
    .stButton>button { border-radius: 12px; font-weight: 700; transition: all 0.2s; border: none; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    .xp-badge { background: #ffd700; color: #000; padding: 10px; border-radius: 10px; text-align: center; font-weight: 900; font-size: 20px; border: 3px solid #ffaa00; margin-bottom: 20px; }
    
    /* Lives Display Top Right */
    .lives-container { display: flex; justify-content: flex-end; font-size: 24px; margin-top: -40px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

def play_sound(sound_type):
    if sound_type == "correct":
        audio_html = """<audio autoplay="true" src="https://assets.mixkit.co/active_storage/sfx/2000/2000-preview.mp3"></audio>"""
    else:
        audio_html = """<audio autoplay="true" src="https://assets.mixkit.co/active_storage/sfx/2003/2003-preview.mp3"></audio>"""
    st.markdown(audio_html, unsafe_allow_html=True)

# --- HARD RANDOM VOCABULARY DATABASE ---
HARD_WORDS = [
    {"term": "Obfuscate", "definition": "To make unclear or unintelligible."},
    {"term": "Pragmatic", "definition": "Dealing with things sensibly and realistically."},
    {"term": "Ephemeral", "definition": "Lasting for a very short time."},
    {"term": "Ubiquitous", "definition": "Present, appearing, or found everywhere."},
    {"term": "Mitochondria", "definition": "The powerhouse of the cell, generating ATP."},
    {"term": "Entropy", "definition": "A measure of disorder or randomness in a system."},
    {"term": "Catalyst", "definition": "A substance that increases the rate of a chemical reaction."},
    {"term": "Algorithm", "definition": "A process or set of rules to be followed in calculations."},
    {"term": "Paradigm", "definition": "A typical example or pattern of something; a model."},
    {"term": "Sycophant", "definition": "A person who acts obsequiously toward someone important."},
    {"term": "Zeitgeist", "definition": "The defining spirit or mood of a particular period of history."},
    {"term": "Quantum", "definition": "A discrete quantity of energy proportional in magnitude to the frequency of the radiation."},
    {"term": "Stoichiometry", "definition": "The relationship between the relative quantities of substances taking part in a reaction."}
]

# --- STATE MANAGEMENT ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "flashcards" not in st.session_state: st.session_state.flashcards = random.sample(HARD_WORDS, 5)

if "active_mode" not in st.session_state: st.session_state.active_mode = "Flashcards"
if "current_index" not in st.session_state: st.session_state.current_index = 0
if "is_flipped" not in st.session_state: st.session_state.is_flipped = False
if "learn_options" not in st.session_state: st.session_state.learn_options = []
if "learn_feedback" not in st.session_state: st.session_state.learn_feedback = None

# Match Game State
if "match_selected_term" not in st.session_state: st.session_state.match_selected_term = None
if "match_matched" not in st.session_state: st.session_state.match_matched = []
if "match_start_time" not in st.session_state: st.session_state.match_start_time = None
if "match_moves" not in st.session_state: st.session_state.match_moves = 0
if "match_lives" not in st.session_state: st.session_state.match_lives = 5

# Scramble Game State
if "scramble_card" not in st.session_state: st.session_state.scramble_card = None
if "scramble_letters" not in st.session_state: st.session_state.scramble_letters = []
if "scramble_answer" not in st.session_state: st.session_state.scramble_answer = ""

# True/False Game State
if "tf_score" not in st.session_state: st.session_state.tf_score = 0
if "tf_lives" not in st.session_state: st.session_state.tf_lives = 5
if "tf_playing" not in st.session_state: st.session_state.tf_playing = False
if "tf_current" not in st.session_state: st.session_state.tf_current = None
if "tf_is_correct" not in st.session_state: st.session_state.tf_is_correct = True
if "tf_answered" not in st.session_state: st.session_state.tf_answered = False
if "tf_feedback" not in st.session_state: st.session_state.tf_feedback = ""

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
    
    st.header("👋 Welcome to StudySync!")
    st.write("""
    **StudySync Arcade** turns boring vocabulary and facts into fun, fast-paced games. 
    Earn XP, build streaks, and master your deck!
    """)
    
    with st.expander("📖 How to Use", expanded=True):
        st.markdown("""
        **1. Generate a Deck:** Type a topic in the box below and hit Generate.
        
        **2. Pick a Mode:** Use the menu at the top of the screen.
        
        **3. Play & Learn:**
        *   **📇 Flashcards:** Flip and memorize.
        *   **🧠 Learn:** Pick the right definition.
        *   **📝 Test:** Multiple-choice quiz.
        *   **🎮 Match Game:** Race the clock to pair terms (You have 5 lives).
        *   **🧩 Scramble:** Unscramble the hidden word.
        *   **⚖️ True/False:** Survival mode (You have 5 lives).
        """)
        
    st.divider()
    
    st.subheader("🤖 AI Deck Generator")
    topic = st.text_input("Topic:", placeholder="e.g., Biology, Space, History")
    
    if st.button("✨ Generate Deck", type="primary", use_container_width=True):
        if not topic.strip():
            st.session_state.flashcards = random.sample(HARD_WORDS, 5)
            st.session_state.current_index = 0
            st.session_state.learn_feedback = None
            st.success("Loaded 5 random hard words!")
            st.rerun()
        else:
            with st.spinner("AI is cooking up your cards..."):
                try:
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
                        st.session_state.learn_feedback = None
                        st.success(f"Loaded {len(new_cards)} cards!")
                        st.rerun()
                    else:
                        st.error("Server busy. Try again.")
                except Exception as e:
                    st.error("Error parsing AI response. Try again.")
    
    st.divider()
    st.caption(f"Deck Status: **{len(st.session_state.flashcards)}** active cards.")

# --- MAIN UI ---
st.title("⚡ StudySync Arcade")

modes = ["Flashcards", "Learn", "Test", "Match Game", "Scramble", "True/False"]
mode = st.radio("Select Mode:", modes, horizontal=True, label_visibility="collapsed")

if mode != st.session_state.active_mode:
    st.session_state.active_mode = mode
    st.session_state.is_flipped = False
    st.session_state.learn_feedback = None
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

    # 3. TEST (MULTIPLE CHOICE)
    elif st.session_state.active_mode == "Test":
        st.subheader("📝 Multiple Choice Test")
        
        if "mcq_current" not in st.session_state:
            st.session_state.mcq_current = 0
            st.session_state.mcq_score = 0
            st.session_state.mcq_options = []
            st.session_state.mcq_answered = False

        if st.session_state.mcq_current < len(st.session_state.flashcards):
            card = st.session_state.flashcards[st.session_state.mcq_current]
            st.write(f"**Question {st.session_state.mcq_current + 1} of {len(st.session_state.flashcards)}**")
            st.progress((st.session_state.mcq_current) / len(st.session_state.flashcards))
            
            if not st.session_state.mcq_options:
                wrong_cards = [c for c in st.session_state.flashcards if c["term"] != card["term"]]
                opts = [card["definition"]] + [c["definition"] for c in random.sample(wrong_cards, min(3, len(wrong_cards)))]
                random.shuffle(opts)
                st.session_state.mcq_options = opts

            st.info(f"What is the definition of **{card['term']}**?")
            
            for opt in st.session_state.mcq_options:
                if st.button(opt, use_container_width=True, disabled=st.session_state.mcq_answered):
                    if opt == card["definition"]:
                        st.success("✅ Correct! +10 XP")
                        st.session_state.xp += 10
                        st.session_state.mcq_score += 1
                        play_sound("correct")
                    else:
                        st.error(f"❌ Wrong! It was: {card['definition']}")
                        play_sound("wrong")
                    st.session_state.mcq_answered = True
                    st.rerun()
                    
            if st.session_state.mcq_answered:
                if st.button("Next Question ➡️", type="primary"):
                    st.session_state.mcq_current += 1
                    st.session_state.mcq_options = []
                    st.session_state.mcq_answered = False
                    st.rerun()
        else:
            st.success(f"🎉 Test Complete! Score: {st.session_state.mcq_score}/{len(st.session_state.flashcards)}")
            st.balloons()
            if st.button("Retake Test"):
                st.session_state.mcq_current = 0
                st.session_state.mcq_score = 0
                st.session_state.mcq_options = []
                st.session_state.mcq_answered = False
                st.rerun()

    # 4. MATCH GAME (Now with Lives)
    elif st.session_state.active_mode == "Match Game":
        st.subheader("🎮 Match Game")
        
        # Initialize game
        if st.session_state.match_start_time is None:
            st.session_state.match_start_time = time.time()
            st.session_state.match_matched = []
            st.session_state.match_selected_term = None
            st.session_state.match_moves = 0
            st.session_state.match_lives = 5
            game_cards = random.sample(st.session_state.flashcards, min(6, len(st.session_state.flashcards)))
            st.session_state.match_game_cards = game_cards
            
        # Display Lives Top Right
        st.markdown(f"<div class='lives-container'>Lives: {'❤️' * st.session_state.match_lives}</div>", unsafe_allow_html=True)
        
        # Game Over Check
        if st.session_state.match_lives <= 0:
            st.error("💀 Game Over! You ran out of lives.")
            if st.button("Play Again", type="primary"):
                st.session_state.match_start_time = None
                st.rerun()
                
        # Win Check
        elif len(st.session_state.match_matched) == len(st.session_state.match_game_cards):
            elapsed = round(time.time() - st.session_state.match_start_time, 1)
            st.success(f"🎉 Victory! Matched in {elapsed} seconds with {st.session_state.match_moves} moves!")
            st.balloons()
            if st.button("Play Again"):
                st.session_state.match_start_time = None; st.rerun()
                
        # Gameplay
        else:
            if "last_refresh" not in st.session_state: st.session_state.last_refresh = time.time()
            if time.time() - st.session_state.last_refresh > 1.0:
                st.session_state.last_refresh = time.time()
                st.rerun()

            if st.session_state.match_selected_term:
                st.markdown(f"<h4 style='text-align: center; color: #4f46e5;'>👉 I am looking for the definition of: <u>{st.session_state.match_selected_term}</u></h4>", unsafe_allow_html=True)
            else:
                st.markdown("<h4 style='text-align: center; color: #888;'>👇 Click a Term below to pick it up</h4>", unsafe_allow_html=True)
            
            elapsed = round(time.time() - st.session_state.match_start_time, 1)
            st.write(f"⏱️ Time: **{elapsed}s** | 🔀 Moves: **{st.session_state.match_moves}**")
            st.divider()
            
            terms = [c["term"] for c in st.session_state.match_game_cards if c["term"] not in st.session_state.match_matched]
            defs = [c["definition"] for c in st.session_state.match_game_cards if c["definition"] not in st.session_state.match_matched]
            random.shuffle(terms)
            random.shuffle(defs)
            
            def select_term(term):
                st.session_state.match_selected_term = term

            def check_definition(definition):
                if st.session_state.match_selected_term:
                    st.session_state.match_moves += 1
                    correct_def = next(c["definition"] for c in st.session_state.match_game_cards if c["term"] == st.session_state.match_selected_term)
                    
                    if definition == correct_def:
                        st.session_state.match_matched.append(st.session_state.match_selected_term)
                        st.session_state.match_selected_term = None
                        play_sound("correct")
                    else:
                        st.session_state.match_lives -= 1
                        st.session_state.match_selected_term = None
                        play_sound("wrong")

            col1, col2 = st.columns(2)
            with col1:
                st.write("### 📦 Terms")
                for t in terms:
                    btn_type = "primary" if st.session_state.match_selected_term == t else "secondary"
                    st.button(t, key=f"term_{t}", use_container_width=True, type=btn_type, on_click=select_term, args=(t,))
                        
            with col2:
                st.write("### 🎯 Definitions")
                for d in defs:
                    st.button(d, key=f"def_{d}", use_container_width=True, on_click=check_definition, args=(d,))

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

        target_word = st.session_state.scramble_card["term"].replace(" ", "").upper()
        
        st.info(f"**Clue:** {st.session_state.scramble_card['definition']}")
        
        blanks = " ".join(["_" for _ in target_word])
        st.markdown(f"<h3 style='letter-spacing: 10px; color: #4f46e5;'>{blanks}</h3>", unsafe_allow_html=True)
        
        st.write(f"### Your Answer: **{st.session_state.scramble_answer if st.session_state.scramble_answer else ''}**")
        
        cols = st.columns(6)
        for i, letter in enumerate(st.session_state.scramble_letters):
            if cols[i % 6].button(letter, key=f"letter_{i}", use_container_width=True):
                st.session_state.scramble_answer += letter
                st.session_state.scramble_letters.pop(i)
                st.rerun()
                
        if st.button("🔄 Reset Word", use_container_width=True):
            st.session_state.scramble_card = None; st.rerun()
            
        if st.session_state.scramble_answer == target_word:
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

    # 6. TRUE / FALSE GAME (Now with Lives Top Right)
    elif st.session_state.active_mode == "True/False":
        st.subheader("⚖️ True or False (Survival)")
        
        # Start Screen
        if not st.session_state.tf_playing:
            st.write(f"🏆 **High Score:** {st.session_state.tf_score}")
            if st.button("▶️ Start Survival Mode", type="primary"):
                st.session_state.tf_playing = True
                st.session_state.tf_score = 0
                st.session_state.tf_lives = 5
                st.session_state.tf_answered = False
                st.session_state.tf_current = random.choice(st.session_state.flashcards)
                st.session_state.tf_is_correct = random.choice([True, False])
                st.rerun()
        
        # Game Over Screen
        elif st.session_state.tf_lives <= 0:
            st.markdown(f"<div class='lives-container'>Lives: {'❤️' * st.session_state.tf_lives}</div>", unsafe_allow_html=True)
            st.error(f"💀 Game Over! You ran out of lives. Final Streak: {st.session_state.tf_score}")
            if st.button("Play Again", type="primary"):
                st.session_state.tf_playing = False
                st.rerun()
                
        # Gameplay Screen
        else:
            # Display Lives Top Right
            st.markdown(f"<div class='lives-container'>Lives: {'❤️' * st.session_state.tf_lives}</div>", unsafe_allow_html=True)
            
            st.write(f"🔥 **Streak:** {st.session_state.tf_score}")
            
            # Determine the displayed definition
            shown_def = st.session_state.tf_current["definition"]
            if not st.session_state.tf_is_correct:
                wrong_cards = [c for c in st.session_state.flashcards if c["term"] != st.session_state.tf_current["term"]]
                if wrong_cards:
                    shown_def = random.choice(wrong_cards)["definition"]
            
            # Display Question
            st.markdown(f"### {st.session_state.tf_current['term']}")
            st.info(f"*{shown_def}*")
            
            # Feedback
            if st.session_state.tf_answered:
                if st.session_state.tf_feedback == "correct":
                    st.success("✅ Correct! +5 XP")
                else:
                    st.error(f"❌ Wrong! The correct definition is: {st.session_state.tf_current['definition']}")
                
                if st.button("Next Question ➡️", type="primary"):
                    st.session_state.tf_answered = False
                    st.session_state.tf_current = random.choice(st.session_state.flashcards)
                    st.session_state.tf_is_correct = random.choice([True, False])
                    st.rerun()
                    
            # Buttons (only show if not answered yet)
            else:
                col1, col2 = st.columns(2)
                if col1.button("✅ TRUE", use_container_width=True, type="primary"):
                    st.session_state.tf_answered = True
                    if st.session_state.tf_is_correct:
                        st.session_state.tf_score += 1
                        st.session_state.xp += 5
                        st.session_state.tf_feedback = "correct"
                        play_sound("correct")
                    else:
                        st.session_state.tf_lives -= 1
                        st.session_state.tf_feedback = "wrong"
                        play_sound("wrong")
                    st.rerun()
                        
                if col2.button("❌ FALSE", use_container_width=True, type="secondary"):
                    st.session_state.tf_answered = True
                    if not st.session_state.tf_is_correct:
                        st.session_state.tf_score += 1
                        st.session_state.xp += 5
                        st.session_state.tf_feedback = "correct"
                        play_sound("correct")
                    else:
                        st.session_state.tf_lives -= 1
                        st.session_state.tf_feedback = "wrong"
                        play_sound("wrong")
                    st.rerun()
