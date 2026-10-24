"""
JanSahayak - Accessible Voice-First Banking Guidance & Request Preparation
Streamlit Application for Customers with Limited Literacy & Demo Staff Review Portal.
"""

import streamlit as st
import io
import time
from datetime import datetime

from orchestrator import orchestrator, SharedSessionState
from speech_service import speech_service
from llm_service import llm_service
from database import (
    list_requests,
    get_request_by_ref,
    get_audit_trail,
    update_request_status,
    resubmit_returned_request
)
from knowledge import OFFICIAL_KNOWLEDGE_BASE, get_record_by_id
from confirmation_parser import parse_customer_confirmation
from agents.intake_agent import get_quick_options, DuplicateInputGuard
from translations import (
    t,
    get_status_label,
    get_status_badge,
    get_phase_label,
    STATUS_LABELS
)

# Streamlit Page Config
st.set_page_config(
    page_title="JanSahayak",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Accessible CSS styling
st.markdown("""
<style>
    /* High contrast, large legible typography */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    .big-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0d47a1;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #424242;
        margin-bottom: 1rem;
    }
    .voice-box {
        background-color: #e3f2fd;
        border-left: 6px solid #1976d2;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1.2rem;
    }
    .voice-text {
        font-size: 1.3rem;
        font-weight: 600;
        color: #0d47a1;
        line-height: 1.5;
    }
    .scheme-card {
        border: 2px solid #bbdefb;
        border-radius: 10px;
        padding: 1.2rem;
        background: #ffffff;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .scheme-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #1565c0;
    }
    .source-tag {
        font-size: 0.85rem;
        color: #555;
        background: #f5f5f5;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-top: 6px;
    }
    .ref-badge {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1b5e20;
        background: #e8f5e9;
        padding: 10px 20px;
        border-radius: 8px;
        display: inline-block;
        border: 2px dashed #4caf50;
    }
    .stButton>button {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.4rem !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "state" not in st.session_state:
    st.session_state.state = orchestrator.create_new_session("hi")

if "active_portal" not in st.session_state:
    st.session_state.active_portal = "customer"

if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# Duplicate-submission guard for typed text and quick-option chips. Scoped to
# session + phase + pending field and disarmed by any state change, so repeated
# valid answers and corrections are never blocked (see DuplicateInputGuard).
if "input_guard" not in st.session_state:
    st.session_state.input_guard = DuplicateInputGuard()

state: SharedSessionState = st.session_state.state
lang: str = state.language


# ==============================================================================
# SIDEBAR CONTROLS & DEMO INFORMATION
# ==============================================================================
with st.sidebar:
    st.markdown(f"### 🏦 **{t('app_title', lang)}**")
    st.caption(t("app_caption", lang))
    st.markdown("---")

    # Portal Selector - internal keys 'customer' and 'staff' with clean display translation
    portal_options = ["customer", "staff"]
    portal_choice = st.radio(
        t("select_portal", lang),
        options=portal_options,
        format_func=lambda x: t("portal_customer", lang) if x == "customer" else t("portal_staff", lang),
        index=0 if st.session_state.active_portal == "customer" else 1,
        key="portal_selector_radio"
    )
    st.session_state.active_portal = portal_choice

    st.markdown("---")

    # Language Switcher
    st.markdown(f"#### 🌐 {t('select_language', lang)}")
    lang_col1, lang_col2 = st.columns(2)
    with lang_col1:
        if st.button("🇮🇳 हिन्दी", use_container_width=True, type="primary" if state.language == "hi" else "secondary", key="btn_lang_hi"):
            orchestrator.set_language(state, "hi")
            st.rerun()
    with lang_col2:
        if st.button("🇬🇧 English", use_container_width=True, type="primary" if state.language == "en" else "secondary", key="btn_lang_en"):
            orchestrator.set_language(state, "en")
            st.rerun()

    st.markdown("---")

    # Active Agent & LLM Status Indicator
    st.markdown(f"#### 🤖 {t('system_status', lang)}")
    st.markdown(f"**{t('active_agent', lang)}** `{state.active_agent}`")
    st.markdown(f"**{t('current_phase', lang)}** `{get_phase_label(state.current_phase, lang)}`")

    provider_info = llm_service.get_provider_status(language=lang)
    st.info(provider_info["label"])

    st.markdown("---")
    st.markdown(f"#### 🔄 {t('session_controls', lang)}")
    if st.button(t("new_session", lang), use_container_width=True, key="btn_new_session_sidebar"):
        st.session_state.state = orchestrator.create_new_session(state.language)
        st.session_state.last_processed_audio = None
        st.session_state.input_guard.reset()
        st.rerun()

    st.markdown("---")
    st.markdown(t("sidebar_safety_disclaimer", lang), unsafe_allow_html=True)


# ==============================================================================
# VIEW 1: CUSTOMER PORTAL
# ==============================================================================
if st.session_state.active_portal == "customer":

    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f'<div class="big-title">{t("customer_title", lang)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sub-title">{t("customer_subtitle", lang)}</div>', unsafe_allow_html=True)

    with col_h2:
        # Quick Status Lookup button
        lookup_label = t("track_status_btn", lang)
        if st.button(lookup_label, use_container_width=True, key="btn_goto_tracking"):
            state.current_phase = "STATUS_TRACKING"
            st.rerun()

    # Journey Navigation Tabs / Steps Bar
    phases = ["INTAKE", "SCHEME_ADVISORY", "CONFIRMATION", "SUBMITTED"]
    step_keys = ["step_details", "step_schemes", "step_review", "step_track"]

    step_cols = st.columns(4)
    for idx, p in enumerate(phases):
        is_active = (state.current_phase == p) or (state.current_phase == "STATUS_TRACKING" and p == "SUBMITTED")
        label = t(step_keys[idx], lang)
        with step_cols[idx]:
            if is_active:
                st.markdown(f"**🟦 {label}**")
            else:
                st.markdown(f"<span style='color:gray;'>▫️ {label}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # Spoken Audio Guidance Banner (TTS Playback)
    # Show the text immediately; synthesize (cached) audio afterwards so the UI isn't blocked.
    if state.last_spoken_text:
        st.markdown(f"""
        <div class="voice-box">
            <span style="font-size:1.4rem;">🔊</span> 
            <span class="voice-text">"{state.last_spoken_text}"</span>
        </div>
        """, unsafe_allow_html=True)

        audio_bytes = speech_service.synthesize_speech(state.last_spoken_text, language=state.language)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")

    # Error message if any
    if state.error_message:
        st.error(state.error_message)

    # --------------------------------------------------------------------------
    # SUB-VIEW A: INTAKE PHASE
    # --------------------------------------------------------------------------
    if state.current_phase == "INTAKE":
        st.markdown(f"### 🗣️ {t('intake_heading', lang)}")

        input_col1, input_col2 = st.columns([1, 1])

        with input_col1:
            st.markdown(f"#### 🎙️ {t('microphone', lang)}")
            audio_input = st.audio_input(
                label=t("press_mic_speak", lang),
                key="audio_mic_input"
            )

            if audio_input is not None and audio_input != st.session_state.last_processed_audio:
                st.session_state.last_processed_audio = audio_input
                audio_bytes = audio_input.read()
                with st.spinner(t("transcribing", lang)):
                    success, transcript, _ = speech_service.transcribe_audio_bytes(audio_bytes, language=state.language)
                    if success:
                        st.success(f"{t('heard_prefix', lang)} '{transcript}'")
                        orchestrator.handle_user_input(state, transcript)
                        st.rerun()
                    else:
                        st.warning(transcript)

        with input_col2:
            st.markdown(f"#### ⌨️ {t('text_fallback', lang)}")
            user_text = st.text_input(
                t("type_here", lang),
                placeholder=t("type_placeholder", lang),
                key="text_customer_input"
            )
            submit_label = t("send_btn", lang)
            if st.button(submit_label, type="primary", key="btn_text_send"):
                if user_text.strip():
                    processed, _ = st.session_state.input_guard.submit(
                        state, user_text, orchestrator.handle_user_input
                    )
                    if processed:
                        st.rerun()

        # Quick Choice Chips for current slot (language-pure)
        pending_slot = state.pending_slot or "name"
        quick_options = get_quick_options(pending_slot, language=lang)

        if quick_options:
            st.markdown(f"##### ⚡ {t('quick_options_heading', lang)}")
            chip_cols = st.columns(len(quick_options))
            for i, opt in enumerate(quick_options):
                with chip_cols[i]:
                    if st.button(opt, key=f"chip_{pending_slot}_{i}", use_container_width=True):
                        processed, _ = st.session_state.input_guard.submit(
                            state, opt, orchestrator.handle_user_input
                        )
                        if processed:
                            st.rerun()

        # Current Gathered Profile Summary Card
        st.markdown("---")
        st.markdown(f"#### 📋 {t('recorded_profile_heading', lang)}")
        p_cols = st.columns(4)
        with p_cols[0]:
            st.metric(t("metric_name", lang), state.customer_profile.get("name") or "—")
        with p_cols[1]:
            st.metric(t("metric_loc", lang), state.customer_profile.get("location") or "—")
        with p_cols[2]:
            st.metric(t("metric_occ", lang), state.customer_profile.get("occupation") or "—")
        with p_cols[3]:
            st.metric(t("metric_purp", lang), state.customer_profile.get("purpose") or "—")

    # --------------------------------------------------------------------------
    # SUB-VIEW B: SCHEME ADVISORY PHASE
    # --------------------------------------------------------------------------
    elif state.current_phase == "SCHEME_ADVISORY":
        st.markdown(f"### 🏦 {t('schemes_heading', lang)}")
        st.caption(t("schemes_caption", lang))

        # Voice input for low-literacy customers to speak their scheme selection
        st.markdown(f"#### 🎙️ {t('voice_scheme_heading', lang)}")
        v_sch_col1, v_sch_col2 = st.columns([1, 1])
        with v_sch_col1:
            sch_audio = st.audio_input(
                t("voice_scheme_mic", lang),
                key="audio_scheme_select"
            )
            if sch_audio is not None and sch_audio != st.session_state.last_processed_audio:
                st.session_state.last_processed_audio = sch_audio
                audio_bytes = sch_audio.read()
                success, transcript, _ = speech_service.transcribe_audio_bytes(audio_bytes, language=state.language)
                if success:
                    st.success(f"{t('heard_prefix', lang)} '{transcript}'")
                    orchestrator.handle_user_input(state, transcript)
                    st.rerun()
                else:
                    st.warning(transcript)
        with v_sch_col2:
            st.info(t("voice_scheme_tip", lang))

        if state.recommended_schemes:
            cols = st.columns(len(state.recommended_schemes))
            for idx, sch in enumerate(state.recommended_schemes):
                with cols[idx]:
                    st.markdown(f"""
                    <div class="scheme-card">
                        <div class="scheme-title">{sch['name']}</div>
                        <p style="font-size:0.95rem; margin-top:8px;">{sch['plain_explanation']}</p>
                        <p><strong>{t('min_balance', lang)}</strong> {sch['min_balance']}</p>
                        <div class="source-tag">
                            📄 <strong>{t('source_available', lang)}</strong> <a href="{sch['official_url']}" target="_blank">{sch['official_source']}</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_label = f"{t('select_scheme_btn', lang)} ({sch['id']})"
                    if st.button(btn_label, key=f"btn_scheme_{sch['id']}", use_container_width=True, type="primary" if idx == 0 else "secondary"):
                        orchestrator.select_scheme_and_proceed(state, sch['id'])
                        st.rerun()

        # Option to re-enter details
        st.markdown("---")
        if st.button(t("go_back_details", lang), key="btn_back_intake_from_schemes"):
            state.current_phase = "INTAKE"
            st.rerun()

    # --------------------------------------------------------------------------
    # SUB-VIEW C: CONFIRMATION & DOCUMENT GUIDANCE PHASE
    # --------------------------------------------------------------------------
    elif state.current_phase == "CONFIRMATION":
        st.markdown(f"### 📄 {t('conf_heading', lang)}")

        rev_col1, rev_col2 = st.columns([1, 1])

        with rev_col1:
            st.markdown(f"#### 👤 {t('summary_heading', lang)}")
            summary_info = state.readback_summary
            if summary_info:
                st.markdown(summary_info.get("display_summary", ""))

            st.markdown("---")
            st.markdown(f"#### 🔊 {t('voice_conf_heading', lang)}")
            st.info(t("voice_conf_info", lang))

            conf_audio = st.audio_input(t("voice_conf_mic", lang), key="conf_audio_input")
            if conf_audio is not None and conf_audio != st.session_state.last_processed_audio:
                st.session_state.last_processed_audio = conf_audio
                audio_bytes = conf_audio.read()
                success, transcript, _ = speech_service.transcribe_audio_bytes(audio_bytes, language=state.language)
                if success:
                    st.success(f"{t('heard_prefix', lang)} '{transcript}'")
                    orchestrator.handle_user_input(state, transcript)
                    st.rerun()

        with rev_col2:
            st.markdown(f"#### 📋 {t('checklist_heading', lang)}")
            doc_info = state.document_guidance
            if doc_info and "checklist" in doc_info:
                for item in doc_info["checklist"]:
                    st.markdown(f"• **{item}**")

                st.warning(doc_info.get("notice", ""))
                st.caption(f"{t('source_available', lang)} {doc_info.get('official_source')}")

        st.markdown("---")
        st.markdown(f"#### 🎯 {t('ready_question', lang)}")

        gate_col1, gate_col2 = st.columns([1, 1])
        with gate_col1:
            if st.button(t("confirm_submit_btn", lang), type="primary", use_container_width=True, key="btn_confirm_submit"):
                state.confirmed_by_customer = True
                orchestrator.execute_submission(state)
                st.rerun()

        with gate_col2:
            if st.button(t("correct_details_btn", lang), type="secondary", use_container_width=True, key="btn_correct_intake"):
                state.current_phase = "INTAKE"
                state.pending_slot = "name"
                state.customer_profile["name"] = ""
                st.rerun()

    # --------------------------------------------------------------------------
    # SUB-VIEW D: SUBMITTED REQUEST & NEXT STEPS
    # --------------------------------------------------------------------------
    elif state.current_phase == "SUBMITTED":
        st.balloons()
        st.markdown(f"### 🎉 {t('submitted_heading', lang)}")

        ref_id = state.submission_id or "JS-2026-XXXX"
        st.markdown(f"""
        <div style="text-align: center; margin: 1.5rem 0;">
            <div class="ref-badge">🔖 {t('reference_badge_label', lang)}: {ref_id}</div>
        </div>
        """, unsafe_allow_html=True)

        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"#### 📋 {t('app_details_heading', lang)}")
            p = state.customer_profile
            st.markdown(f"• **{t('field_name_label', lang)}:** {p.get('name')}")
            st.markdown(f"• **{t('field_loc_label', lang)}:** {p.get('location')}")
            st.markdown(f"• **{t('field_occ_label', lang)}:** {p.get('occupation')}")
            st.markdown(f"• **{t('field_scheme_label', lang)}:** {state.selected_scheme_name}")
            st.markdown(f"• **{t('field_status_label', lang)}:** `{get_status_label('SUBMITTED', lang)}`")

        with info_col2:
            st.markdown(f"#### 📌 {t('next_steps_heading', lang)}")
            st.info(t("next_steps_body", lang))

        st.markdown("---")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button(t("check_status_btn", lang), use_container_width=True, key="btn_track_submitted"):
                state.current_phase = "STATUS_TRACKING"
                st.rerun()
        with btn_c2:
            if st.button(t("new_app_btn", lang), use_container_width=True, key="btn_new_app_submitted"):
                st.session_state.state = orchestrator.create_new_session(state.language)
                st.rerun()

    # --------------------------------------------------------------------------
    # SUB-VIEW E: STATUS TRACKING & RESUBMISSION
    # --------------------------------------------------------------------------
    elif state.current_phase == "STATUS_TRACKING":
        st.markdown(f"### 🔍 {t('tracking_heading', lang)}")

        query_col1, query_col2 = st.columns([3, 1])
        with query_col1:
            ref_input = st.text_input(
                t("enter_ref", lang),
                value=state.submission_id or "",
                placeholder=t("search_placeholder", lang),
                key="input_status_search_ref"
            )
        with query_col2:
            st.write("")
            st.write("")
            search_btn = st.button(t("search_btn", lang), type="primary", use_container_width=True, key="btn_search_status")

        if ref_input.strip():
            status_data = orchestrator.check_status(ref_input.strip(), language=state.language)
            if not status_data["found"]:
                st.error(status_data["spoken_message"])
            else:
                rec = status_data["record"]
                curr_status = rec["status"]

                st.markdown("---")
                # Spoken audio for status
                audio_bytes = speech_service.synthesize_speech(status_data["spoken_message"], language=state.language)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

                st.markdown(f"#### 🔖 {t('reference_badge_label', lang)}: `{rec['reference_id']}`")

                stat_col1, stat_col2 = st.columns(2)
                with stat_col1:
                    badge_icon = get_status_badge(curr_status)
                    status_text = get_status_label(curr_status, lang)
                    st.markdown(f"**{t('field_status_label', lang)}:** `{badge_icon} {status_text}`")
                    st.markdown(f"**{t('field_name_label', lang)}:** {rec['customer_name']}")
                    st.markdown(f"**{t('field_loc_label', lang)}:** {rec['location']}")
                    st.markdown(f"**{t('field_occ_label', lang)}:** {rec['occupation']}")
                    st.markdown(f"**{t('field_scheme_label', lang)}:** {rec['selected_scheme']}")
                    st.markdown(f"**{t('app_date', lang)}** {rec['created_at']}")

                with stat_col2:
                    st.markdown(f"##### 📌 {t('staff_notes_next_steps', lang)}")
                    if rec.get("staff_notes"):
                        st.warning(f"**{t('staff_note_prefix', lang)}** {rec['staff_notes']}")
                    st.info(status_data["next_steps"])

                # If status is RETURNED -> Allow customer correction and resubmission
                if curr_status == "RETURNED":
                    st.markdown("---")
                    st.markdown(f"### ✏️ {t('correct_resubmit_heading', lang)}")
                    st.warning(f"⚠️ **{t('return_reason_heading', lang)}**: {rec.get('staff_notes')}")

                    ref = rec["reference_id"]
                    # Widget-state keys – these are the actual keys that
                    # st.text_input / st.selectbox read and write.
                    wk_name = f"input_corr_name_{ref}"
                    wk_loc  = f"input_corr_loc_{ref}"
                    wk_occ  = f"input_corr_occ_{ref}"
                    wk_sch  = f"input_corr_scheme_{ref}"

                    # Shadow keys (corr_*) kept for backward compat; they
                    # are authoritative only on first load.
                    corr_key_prefix = f"corr_{ref}"

                    # First-time initialisation: populate widget keys from
                    # DB record (or from corr_ shadow if they already exist,
                    # e.g. after a language switch where widgets were deleted
                    # but corr_ values survive).
                    if wk_name not in st.session_state:
                        init_name = st.session_state.get(f"{corr_key_prefix}_name", rec["customer_name"])
                        init_loc  = st.session_state.get(f"{corr_key_prefix}_loc",  rec["location"])
                        init_occ  = st.session_state.get(f"{corr_key_prefix}_occ",  rec["occupation"])
                        st.session_state[wk_name] = init_name
                        st.session_state[wk_loc]  = init_loc
                        st.session_state[wk_occ]  = init_occ
                        # Also initialise shadow keys so they stay in sync
                        st.session_state[f"{corr_key_prefix}_name"] = init_name
                        st.session_state[f"{corr_key_prefix}_loc"]  = init_loc
                        st.session_state[f"{corr_key_prefix}_occ"]  = init_occ

                    if f"{corr_key_prefix}_scheme" not in st.session_state:
                        st.session_state[f"{corr_key_prefix}_scheme"] = rec["selected_scheme"]

                    # 1. Voice Control for speaking corrections
                    st.markdown(f"#### 🎙️ {t('voice_corr_heading', lang)}")
                    ret_col1, ret_col2 = st.columns([1, 1])
                    with ret_col1:
                        ret_audio = st.audio_input(
                            t("voice_corr_mic", lang),
                            key=f"audio_input_ret_{ref}"
                        )
                        if ret_audio is not None and ret_audio != st.session_state.last_processed_audio:
                            st.session_state.last_processed_audio = ret_audio
                            audio_bytes = ret_audio.read()
                            with st.spinner(t("transcribing", lang)):
                                success, transcript, _ = speech_service.transcribe_audio_bytes(audio_bytes, language=state.language)
                                if success:
                                    st.success(f"{t('heard_prefix', lang)} '{transcript}'")
                                    # Extract structured slots from spoken correction
                                    extracted = llm_service.extract_structured_slots(
                                        transcript,
                                        {
                                            "name": st.session_state[wk_name],
                                            "location": st.session_state[wk_loc],
                                            "occupation": st.session_state[wk_occ]
                                        },
                                        language=state.language
                                    )
                                    # Write corrections into the WIDGET keys
                                    # so they appear in the fields on rerun.
                                    if extracted.get("name"):
                                        st.session_state[wk_name] = extracted["name"]
                                        st.session_state[f"{corr_key_prefix}_name"] = extracted["name"]
                                    if extracted.get("location"):
                                        st.session_state[wk_loc] = extracted["location"]
                                        st.session_state[f"{corr_key_prefix}_loc"] = extracted["location"]
                                    if extracted.get("occupation"):
                                        st.session_state[wk_occ] = extracted["occupation"]
                                        st.session_state[f"{corr_key_prefix}_occ"] = extracted["occupation"]
                                    st.rerun()
                                else:
                                    st.warning(transcript)
                    with ret_col2:
                        st.info(t("voice_corr_tip", lang))

                    # 2. Editable review fields (widget keys are stable
                    #    across language switches because they use the
                    #    reference ID, not translatable text).
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        new_name = st.text_input(
                            t("input_name_label", lang),
                            key=wk_name
                        )
                        new_loc = st.text_input(
                            t("input_loc_label", lang),
                            key=wk_loc
                        )
                    with edit_col2:
                        new_occ = st.text_input(
                            t("input_occ_label", lang),
                            key=wk_occ
                        )
                        scheme_options = ["PMJDY", "BSBDA", "REGULAR_SAVINGS", "PMSBY", "PMJJBY", "APY"]
                        curr_scheme_idx = scheme_options.index(rec["selected_scheme"]) if rec["selected_scheme"] in scheme_options else 0
                        new_scheme = st.selectbox(
                            t("input_scheme_label", lang),
                            options=scheme_options,
                            index=curr_scheme_idx,
                            key=wk_sch
                        )

                    # Sync shadow keys from widget values (for persistence
                    # across language switches where widgets are destroyed).
                    st.session_state[f"{corr_key_prefix}_name"] = new_name
                    st.session_state[f"{corr_key_prefix}_loc"] = new_loc
                    st.session_state[f"{corr_key_prefix}_occ"] = new_occ
                    st.session_state[f"{corr_key_prefix}_scheme"] = new_scheme

                    # 3. Spoken Confirmation for Resubmission
                    st.markdown(f"#### 🔊 {t('voice_resubmit_heading', lang)}")
                    ret_conf_col1, ret_conf_col2 = st.columns([1, 1])
                    voice_resubmit_triggered = False
                    with ret_conf_col1:
                        ret_conf_audio = st.audio_input(
                            t("voice_resubmit_mic", lang),
                            key=f"audio_ret_conf_{rec['reference_id']}"
                        )
                        if ret_conf_audio is not None and ret_conf_audio != st.session_state.last_processed_audio:
                            st.session_state.last_processed_audio = ret_conf_audio
                            audio_bytes = ret_conf_audio.read()
                            success, transcript, _ = speech_service.transcribe_audio_bytes(audio_bytes, language=state.language)
                            if success:
                                parsed = parse_customer_confirmation(transcript, language=state.language)
                                if parsed.is_confirmed:
                                    st.success(f"{t('voice_consent_received', lang)} '{transcript}'")
                                    voice_resubmit_triggered = True
                                else:
                                    feedback = parsed.feedback_message_hi if state.language == "hi" else parsed.feedback_message_en
                                    rej_label = "अस्वीकृत" if state.language == "hi" else "Rejected"
                                    st.warning(f"{rej_label} ({parsed.decision}): {feedback}")

                    with ret_conf_col2:
                        resubmit_conf = st.checkbox(
                            t("confirm_checkbox", lang),
                            value=voice_resubmit_triggered,
                            key=f"chk_resubmit_conf_{rec['reference_id']}"
                        )

                    if st.button(t("resubmit_btn", lang), type="primary", key=f"btn_resubmit_action_{rec['reference_id']}") or voice_resubmit_triggered:
                        if not resubmit_conf and not voice_resubmit_triggered:
                            st.error(t("resubmit_check_error", lang))
                        else:
                            success, r_msg = resubmit_returned_request(
                                rec["reference_id"],
                                {
                                    "customer_name": new_name,
                                    "location": new_loc,
                                    "occupation": new_occ,
                                    "selected_scheme": new_scheme
                                }
                            )
                            if success:
                                st.success(t("resubmit_success", lang))
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(r_msg)

                # Audit History Trail
                st.markdown("---")
                with st.expander(f"📜 {t('audit_trail_expander', lang)}"):
                    audit_list = status_data.get("audit_trail", [])
                    for a in audit_list:
                        st.markdown(f"• `{a['timestamp']}` | **[{a['actor']}]** {a['action']} — *{a.get('details', '')}*")

        st.markdown("---")
        if st.button(t("back_to_home", lang), key="btn_back_home_from_tracking"):
            state.current_phase = "INTAKE"
            st.rerun()


# ==============================================================================
# VIEW 2: DEMO BANK STAFF REVIEW PORTAL
# ==============================================================================
elif st.session_state.active_portal == "staff":
    st.markdown(f'<div class="big-title">👥 {t("staff_title", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">{t("staff_subtitle", lang)}</div>', unsafe_allow_html=True)

    st.warning(t("staff_disclaimer", lang))

    # Filter Controls (internal codes kept intact; format_func translates display)
    filter_col1, filter_col2 = st.columns([2, 2])
    with filter_col1:
        status_filter = st.selectbox(
            t("filter_by_status", lang),
            options=["ALL", "SUBMITTED", "APPROVED_FOR_PROCESSING", "RETURNED", "REJECTED"],
            format_func=lambda s: get_status_label(s, lang),
            index=0,
            key="staff_status_filter_select"
        )
    with filter_col2:
        st.write("")
        st.write("")
        if st.button(t("refresh_list", lang), key="btn_staff_refresh"):
            st.rerun()

    requests_list = list_requests(status_filter=status_filter)
    st.markdown(f"**{t('total_requests', lang)}** `{len(requests_list)}`")

    if not requests_list:
        st.info(t("no_requests", lang))
    else:
        # Display each request in an expandable card
        for req in requests_list:
            ref = req["reference_id"]
            status = req["status"]

            # Visual badge color and clean translated status text
            badge_icon = get_status_badge(status)
            status_text = get_status_label(status, lang)

            expander_title = (
                f"{badge_icon} **[{ref}]** {req['customer_name']} ({req['location']}) — "
                f"{req['selected_scheme']} | {t('field_status_label', lang)}: `{status_text}`"
            )

            with st.expander(expander_title):
                r_c1, r_c2 = st.columns([1, 1])

                with r_c1:
                    st.markdown(f"##### 👤 {t('staff_profile_heading', lang)}")
                    st.markdown(f"{t('staff_profile_name', lang)} {req['customer_name']}")
                    st.markdown(f"{t('staff_profile_loc', lang)} {req['location']}")
                    st.markdown(f"{t('staff_profile_occ', lang)} {req['occupation']}")
                    st.markdown(f"{t('staff_profile_income', lang)} {req.get('income_bracket', 'उपलब्ध नहीं' if lang == 'hi' else 'Not Available')}")
                    st.markdown(f"{t('staff_profile_purpose', lang)} {req['purpose']}")
                    st.markdown(f"{t('staff_profile_scheme', lang)} {req['selected_scheme']}")
                    st.markdown(f"{t('staff_profile_lang', lang)} {req['language']}")
                    st.markdown(f"{t('staff_profile_time', lang)} {req['created_at']}")
                    if req.get("staff_notes"):
                        st.markdown(f"{t('staff_profile_notes', lang)} *{req['staff_notes']}*")

                with r_c2:
                    st.markdown(f"##### ⚖️ {t('staff_action_heading', lang)}")
                    st.caption(t("staff_action_caption", lang))
                    staff_reason = st.text_area(
                        t("staff_notes_label", lang),
                        placeholder=t("staff_notes_placeholder", lang),
                        key=f"notes_{ref}"
                    )

                    act_col1, act_col2, act_col3 = st.columns(3)
                    with act_col1:
                        if st.button(t("btn_approve", lang), key=f"app_{ref}", use_container_width=True):
                            note = staff_reason.strip() or t("approve_default_note", lang)
                            ok, msg = update_request_status(ref, "APPROVED_FOR_PROCESSING", note)
                            if ok:
                                st.success(f"{ref} {t('approved_msg', lang)}")
                                time.sleep(0.8)
                                st.rerun()

                    with act_col2:
                        if st.button(t("btn_return", lang), key=f"ret_{ref}", use_container_width=True):
                            if not staff_reason.strip():
                                st.error(t("return_reason_required", lang))
                            else:
                                ok, msg = update_request_status(ref, "RETURNED", staff_reason.strip())
                                if ok:
                                    st.warning(f"{ref} {t('returned_msg', lang)}")
                                    time.sleep(0.8)
                                    st.rerun()

                    with act_col3:
                        if st.button(t("btn_reject", lang), key=f"rej_{ref}", use_container_width=True):
                            if not staff_reason.strip():
                                st.error(t("reject_reason_required", lang))
                            else:
                                ok, msg = update_request_status(ref, "REJECTED", staff_reason.strip())
                                if ok:
                                    st.error(f"{ref} {t('rejected_msg', lang)}")
                                    time.sleep(0.8)
                                    st.rerun()

                # Audit Trail for this request
                st.markdown("---")
                st.markdown(f"##### 📜 {t('audit_trail_heading', lang)}")
                audit_rows = get_audit_trail(ref)
                for a in audit_rows:
                    st.markdown(f"<small>• <strong>{a['timestamp']}</strong> | [{a['actor']}] <code>{a['action']}</code> — {a.get('details', '')}</small>", unsafe_allow_html=True)
