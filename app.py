import json
import random
from collections import defaultdict
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from core import engine as en
from core import storage as db
from core.local_ai import local_model
from core.web_quiz import generate_reference_quiz, google_url

st.set_page_config(page_title='StudyLens AI 2.0',page_icon='🎓',layout='wide')
db.init()
st.title('🎓 StudyLens AI 2.0')
st.caption('Diagnose · Plan · Practise · Improve — no API key required')

for name,default in {'quiz':[], 'results':None,'quiz_key':'','report':'','cards_from_resource':[], 'source_text':''}.items():
    if name not in st.session_state:st.session_state[name]=default

with st.sidebar:
    st.header('Your preparation')
    demo_id=st.text_input('Demo identifier (not a password)','Exhibition Guest').strip() or 'Exhibition Guest'
    exam=st.selectbox('Preparation domain',en.EXAMS,index=en.EXAMS.index('ISC Boards'))
    if exam=='Other / Custom':exam=st.text_input('Specify examination','School examination')
    grade=st.selectbox('Level',['Class 8','Class 9','Class 10','Class 11','Class 12','Graduation','Other'],index=3)
    st.info('Cloud mode: no API key required. Local AI is optional.')
    section=st.radio('Navigate',['🏠 Overview','📝 Diagnostic Test','📊 My Diagnostics','🗓️ Study Planner','🃏 Flashcards','✅ Revision Tracker','🎞️ Learning Reels','💬 Concept Coach','🧪 Same-Score Lab','📚 Source Material'])

st.markdown('''<style>.block-container{max-width:1250px}.stButton button{border-radius:9px}</style>''',unsafe_allow_html=True)

history=db.attempts(demo_id)
all_diagnostics=en.diagnostic(history)
known_topics=list(dict.fromkeys([x['topic'] for x in history]))

# Material is session-scoped; no uploaded book content saved in the SQLite database.
def extract_upload(upload):
    suffix=upload.name.lower()
    if suffix.endswith('.txt') or suffix.endswith('.md'):
        return upload.getvalue().decode('utf-8',errors='replace')
    if suffix.endswith('.pdf'):
        from pypdf import PdfReader
        reader=PdfReader(BytesIO(upload.getvalue()))
        return '\n'.join((p.extract_text() or '') for p in reader.pages[:35])
    if suffix.endswith('.docx'):
        from docx import Document
        return '\n'.join(p.text for p in Document(BytesIO(upload.getvalue())).paragraphs)
    return ''

if section=='🏠 Overview':
    st.subheader('A personalised preparation workbench')
    st.write('Choose your exam, test specific topics, record confidence, and use the four-quadrant diagnostic to decide what to revise next.')
    c1,c2,c3=st.columns(3)
    c1.metric('Questions attempted',len(history))
    c2.metric('Overall accuracy',f"{100*sum(x['correct'] for x in history)/len(history):.0f}%" if history else '—')
    c3.metric('Tracked concepts',len(all_diagnostics))
    st.info('Start with Diagnostic Test. For an instant exhibition demonstration use Same-Score Lab.')
    st.write('**About this demo:** built-in question bank and rule-based study tools work on Streamlit Cloud. Open-ended AI generation requires an optional local model running on your computer. The selected exam is a preparation label; this prototype does not implement every official exam format.')

elif section=='📚 Source Material':
    st.subheader('Your notes and learning resources')
    uploads=st.file_uploader('Upload PDF, DOCX or text (extractable text only)',type=['pdf','docx','txt','md'],accept_multiple_files=True)
    pasted=st.text_area('Or paste your notes',height=180)
    if st.button('Extract material'):
        combined=pasted+'\n'+'\n'.join(extract_upload(f) for f in (uploads or []))
        st.session_state.source_text=combined[:60000]
        st.success(f'Extracted {len(st.session_state.source_text):,} characters into this browser session.')
    text=st.session_state.source_text
    if text:
        with st.expander('Preview extracted text'):st.text(text[:4000])
        st.caption('This can create source-grounded recall cards without AI. True arbitrary MCQ generation from notes requires the optional local language model. Scanned PDFs and video/audio lectures need transcripts/OCR first.')
        snippets=en.extract_candidates(text)
        st.write(f'{len(snippets)} candidate source passages found.')
        if st.button('Create source recall flashcards'):
            n=0
            for snippet in snippets[:12]:
                db.card_add(demo_id,'Uploaded material','Recall and explain this passage:',snippet)
                n+=1
            st.success(f'Added {n} source-excerpt recall cards.')

elif section=='📝 Diagnostic Test':
    st.subheader('Start a diagnostic assessment')
    subjects=sorted(set(x[0] for x in en.SEEDS))
    subject=st.selectbox('Subject',subjects+['Custom subject'],index=subjects.index('Physics'))
    if subject=='Custom subject':
        subject=st.text_input('Subject name','History').strip()
    topic=st.text_input('Enter any topic',value='Motion in a Straight Line',placeholder='e.g. Cell division, World War I, Integration, Photosynthesis').strip()
    difficulty=st.selectbox('Question difficulty',en.DIFFICULTIES,index=1)
    source=st.radio('Question source',[
        'Online references (no API key)',
        'Curated demo bank',
        'Local AI (Ollama; laptop only)'
    ])
    n=st.select_slider('Number of questions',options=[5,10,15,20],value=10)
    if topic:
        st.link_button('🔎 Also search Google for this topic',google_url(topic,exam,grade))
    st.caption('For Physics straight-line motion, StudyLens generates new equation-checked numerical problems and links an open textbook. For other topics, online mode retrieves Wikipedia references and makes template questions. It does not automatically scrape Google or use a generative AI model.')
    if source=='Curated demo bank' and topic:
        available=en.question_bank(subject,topic,difficulty)
        st.caption(f'{len(available)} matching curated items. This small bank may not provide five questions; use Online references for custom topics.')
    if st.button('Generate new assessment',type='primary'):
        try:
            if not topic:
                st.warning('Please enter your topic.');st.stop()
            if source=='Online references (no API key)':
                with st.spinner('Searching public reference pages and preparing your questions...'):
                    if en.is_straight_line_motion(subject, topic):
                        quiz=en.kinematics_quiz(subject,topic,difficulty,n,exam,grade)
                    
                    else:
                        raise ValueError(
                            f"StudyLens does not yet have a validated "
                            f"{exam} question generator for '{topic}' "
                            f"in {subject}. Please choose a supported "
                            f"topic or use the Local AI option. "
                            f"General-knowledge questions will not "
                            f"be substituted for syllabus questions."
                                )

            elif source=='Curated demo bank':
                bank=en.question_bank(subject,topic,difficulty)
                if len(bank)<5:
                    st.warning('Fewer than 5 curated questions are available for this combination. Select Online references instead.');st.stop()
                quiz=en.safe_quiz(bank,n)
            else:
                prompt=(f'Generate at least {n} distinct {difficulty} level questions for {exam}, {grade}, subject {subject}, topic {topic}. '
                    'Respond as JSON object with key "questions", a list of objects with topic, question, options (4 unique strings), answer (exact matching option), and explanation. '
                    'Factual correctness matters. Do not invent source citations. ')
                if st.session_state.source_text:
                    prompt+=' Base questions only on this source excerpt and avoid outside claims: '+st.session_state.source_text[:12000]
                data=local_model(prompt,as_json=True)
                quiz=en.clean_questions(data,subject,topic,difficulty,source='Local model')[:n]
                if len(quiz)<5: raise ValueError('The local model did not return five valid questions. Retry.')
            st.session_state.quiz=quiz
            st.session_state.results=None
            st.session_state.quiz_key=en.uuid_hash(str(random.random()))
            st.rerun()
        except Exception as error:
            st.error(f'Could not create a 5-question assessment: {error}')
    if st.session_state.quiz and st.session_state.results is None:
    quiz = st.session_state.quiz
        if quiz[0].get("source") != "Curated demo bank":
            st.warning(
                "Reference-based and AI-generated questions can be imperfect. "
                "Review source descriptions and answers before relying on results."
            )
    with st.form(f"quiz_{st.session_state.quiz_key}"):
            selected=[];conf=[]
            for i,q in enumerate(quiz):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                selected.append(st.radio('Choose answer',q['options'],index=None,key=f"{st.session_state.quiz_key}_a{i}"))
                conf.append(st.slider('Confidence (1 low – 3 high)',1,3,2,key=f"{st.session_state.quiz_key}_c{i}"))
                st.divider()
            submit=st.form_submit_button('Submit assessment',type='primary')
        if submit:
            if any(v is None for v in selected):st.error('Please answer all questions.')
            else:
                rows=en.score_quiz(quiz,selected,conf)
                db.save_attempt(demo_id,rows)
                st.session_state.results=rows
                st.rerun()
    if st.session_state.results is not None:
        rows=st.session_state.results
        st.success(f"Score: {sum(r['correct'] for r in rows)} / {len(rows)}")
        for r in rows:
            with st.expander(('✅ ' if r['correct'] else '❌ ')+r['question']):
                st.write(f"Your answer: {r['selected']} | Correct: {r['answer']}")
                st.write(r['explanation'])
                if r.get('source_url'):
                    st.link_button('Read supporting reference',r['source_url'])
        st.dataframe(pd.DataFrame(en.diagnostic(rows)),hide_index=True,use_container_width=True)
        st.caption('A short topic diagnostic is uncertain; repeat with varied items before claiming mastery.')

elif section=='📊 My Diagnostics':
    st.subheader('Learning-gap dashboard')
    if not history:st.info('Take a diagnostic test first.')
    else:
        frame=pd.DataFrame(history)
        left,right=st.columns(2)
        left.metric('Attempted',len(frame));right.metric('Accuracy',f"{100*frame['correct'].mean():.1f}%")
        st.dataframe(pd.DataFrame(all_diagnostics),hide_index=True,use_container_width=True)
        topic=frame.groupby(['subject','topic','difficulty'],as_index=False).agg(attempted=('correct','count'),correct=('correct','sum'))
        topic['accuracy']=100*topic['correct']/topic['attempted']
        st.plotly_chart(px.bar(topic,x='topic',y='accuracy',color='difficulty',hover_data=['attempted','subject'],barmode='group',range_y=[0,100],title='Topic accuracy by difficulty'),use_container_width=True)
        attempts=frame.groupby(['assessment','created'],as_index=False).agg(attempted=('correct','count'),correct=('correct','sum'))
        attempts=attempts.sort_values('created').reset_index(drop=True);attempts['test']=range(1,len(attempts)+1);attempts['accuracy']=100*attempts['correct']/attempts['attempted']
        st.plotly_chart(px.line(attempts,x='test',y='accuracy',markers=True,hover_data=['created','attempted'],range_y=[0,100],title='Assessment accuracy by test'),use_container_width=True)
        st.plotly_chart(px.bar(attempts,x='test',y='attempted',title='Number of questions attempted by test'),use_container_width=True)
        st.subheader('Four-quadrant diagnostic')
        diag=pd.DataFrame(all_diagnostics)
        fig=px.scatter(diag,x='accuracy',y='confidence',size='attempted',color='zone',hover_name='topic',range_x=[0,100],range_y=[0,100],title='Accuracy × self-reported confidence')
        fig.add_vline(x=70,line_dash='dash');fig.add_hline(y=67,line_dash='dash')
        st.plotly_chart(fig,use_container_width=True)
        st.caption('Preliminary evidence only. Few questions per concept and mixed difficulty mean quadrant labels are indicative, not psychometric diagnoses.')
        st.download_button('Export attempt history',frame.to_csv(index=False),'studylens_history.csv','text/csv')

elif section=='🗓️ Study Planner':
    st.subheader('N-day study plan')
    days=st.number_input('Days to plan',min_value=1,max_value=365,value=7)
    minutes=st.number_input('Minutes available each day',min_value=10,max_value=600,value=60,step=10)
    suggested=[x['topic'] for x in all_diagnostics if x['accuracy']<80]
    manual=st.text_input('Additional topics (comma separated)','')
    items=list(dict.fromkeys(suggested+[s.strip() for s in manual.split(',') if s.strip()]))
    if st.button('Create plan'):
        st.session_state.plan=en.schedule(items,int(days),int(minutes),exam)
    if st.session_state.get('plan'):
        plan=pd.DataFrame(st.session_state.plan)
        st.dataframe(plan,hide_index=True,use_container_width=True)
        st.download_button('Download plan',plan.to_csv(index=False),'studylens_plan.csv','text/csv')
        st.caption('This is a transparent rule-based schedule, not generative AI.')

elif section=='🃏 Flashcards':
    st.subheader('Flashcard studio')
    with st.form('new_card'):
        topic=st.text_input('Topic','General')
        front=st.text_input('Front (question or prompt)')
        back=st.text_area('Back (answer)')
        add=st.form_submit_button('Save flashcard')
    if add and front.strip() and back.strip():db.card_add(demo_id,topic,front,back);st.success('Card added')
    cards=db.card_get(demo_id)
    if cards:
        index=st.number_input('Card',1,len(cards),1)
        card=cards[index-1]
        st.markdown(f"### {card[2]}")
        if st.toggle('Reveal answer',key=f'reveal_{card[0]}'):st.info(card[3])
        a,b=st.columns(2)
        if a.button('Remembered',key='yes'):db.card_review(card[0],True);st.success('Review scheduled further out')
        if b.button('Forgot',key='no'):db.card_review(card[0],False);st.info('Review scheduled tomorrow')
        st.caption(f'Due: {card[4]} | Interval: {card[5]} day(s)')
        st.dataframe(pd.DataFrame(cards,columns=['id','topic','front','back','due','interval_days']).drop(columns=['id']),hide_index=True)
    else:st.info('Create your first card or import source recall cards under Source Material.')

elif section=='✅ Revision Tracker':
    st.subheader('Revision tracker')
    topics=sorted(set(known_topics+[x['topic'] for x in en.question_bank()]))
    topic=st.selectbox('Topic to update',topics+['Custom topic'])
    if topic=='Custom topic':topic=st.text_input('Topic name','General revision')
    status=st.selectbox('Revision status',['Not started','Learning','Revising','Mastered'])
    if st.button('Save status'):db.revision_set(demo_id,topic,status);st.success('Status saved')
    records=db.revision_get(demo_id)
    if records:st.dataframe(pd.DataFrame(records,columns=['Topic','Status','Updated']),hide_index=True,use_container_width=True)

elif section=='🎞️ Learning Reels':
    st.subheader('Short-form learning feed')
    st.caption('Swipe-style micro-lessons: not hosted videos or generative clips.')
    reels=[dict(topic=x['topic'],front=x['question'],back=x['explanation']) for x in en.question_bank()]
    if known_topics:
        priority=set(x['topic'] for x in all_diagnostics if x['accuracy']<80)
        reels.sort(key=lambda x:0 if x['topic'] in priority else 1)
    idx=st.number_input('Reel',1,len(reels),1)
    reel=reels[idx-1]
    st.markdown(f"#### {reel['topic']}")
    st.markdown(f"### {reel['front']}")
    if st.button('Reveal micro-lesson',key=f'reel_{idx}'):st.info(reel['back'])
    st.progress(idx/len(reels));st.caption(f'{idx} of {len(reels)} cards; select the next number to continue')

elif section=='💬 Concept Coach':
    st.subheader('Concept coach')
    st.write('Cloud mode gives checked explanations from the built-in question bank. Free-form discussion requires Ollama installed and running locally on your own computer.')
    topic=st.selectbox('Choose a topic',sorted({q['topic'] for q in en.question_bank()}))
    snippets=[q for q in en.question_bank() if q['topic']==topic]
    for q in snippets:
        with st.expander(q['question']):st.write(q['explanation'])
    mode=st.checkbox('Use optional local generative coach (Ollama)')
    if mode:
        question=st.text_area('Ask a concept question')
        if st.button('Ask coach') and question.strip():
            try:
                response=local_model(f'You are StudyLens, a careful educational tutor for {exam} ({grade}). Explain step by step and acknowledge uncertainty. User question: {question}')
                st.markdown(response)
            except Exception:st.error('Local model not available. Install and run Ollama on the same laptop as Streamlit, or use built-in explanations on Cloud.')

elif section=='🧪 Same-Score Lab':
    st.subheader('Same marks ≠ same learning profile')
    topics=['Algebra','Trigonometry','Geometry','Functions','Sequences']
    a=[4,4,2,1,1];b=[1,1,4,3,3]
    d=pd.DataFrame({'Topic':topics,'Student A':a,'Student B':b})
    c1,c2=st.columns(2)
    c1.metric('Student A',f'{sum(a)}/20 (60%)');c2.metric('Student B',f'{sum(b)}/20 (60%)')
    st.plotly_chart(px.bar(d.melt('Topic',var_name='Student',value_name='Correct of 4'),x='Topic',y='Correct of 4',color='Student',barmode='group',range_y=[0,4]),use_container_width=True)
    mean_gap=sum(abs(x-y)/4 for x,y in zip(a,b))/len(a)*100
    st.metric('Mean absolute topic accuracy gap',f'{mean_gap:.0f} percentage points')
    st.write('Student A should prioritise Functions and Sequences; Student B should prioritise Algebra and Trigonometry. Equal total marks conceal different patterns of demonstrated knowledge.')
    st.caption('Fictional data, 4 questions per topic. Small samples create substantial uncertainty; this is an illustration, not evidence of stable individual mastery.')

st.divider()
st.caption('StudyLens AI 2.0 · Exhibition prototype · Use fictional IDs · Local SQLite may reset on cloud restart. No public authentication. Generated questions require verification.')
