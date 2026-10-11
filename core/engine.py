import hashlib
import json
import random
import re
from datetime import date, timedelta

EXAMS = ["IIT-JEE Main", "IIT-JEE Advanced", "IIT-JEE Main + Advanced", "NEET", "SAT", "ACT", "IELTS", "ISC Boards", "ICSE Boards", "CBSE Boards", "UPSC-CSE", "NDA", "Other / Custom"]
DIFFICULTIES = ["Easy", "Intermediate", "Hard"]

# Hand-reviewed illustrative seed items; these are not official exam questions.
SEEDS = [
 ("Mathematics", "Quadratic Equations", "Easy", "What are the roots of x² − 5x + 6 = 0?", ["2 and 3", "−2 and −3", "1 and 6", "0 and 5"], "2 and 3", "Factor as (x−2)(x−3)=0."),
 ("Mathematics", "Quadratic Equations", "Intermediate", "What is the discriminant of 2x² + 4x + 3 = 0?", ["−8", "8", "16", "−4"], "−8", "b²−4ac = 16−24 = −8."),
 ("Mathematics", "Quadratic Equations", "Hard", "If x² − 2kx + 9 = 0 has equal real roots, which values can k take?", ["−3 or 3", "3 only", "−9 or 9", "0"], "−3 or 3", "The discriminant is 4k²−36=0, hence k=±3."),
 ("Mathematics", "Sets", "Easy", "What is {1,2} ∩ {2,3}?", ["{2}", "{1,2,3}", "{1,3}", "{}"], "{2}", "Intersection contains common elements."),
 ("Mathematics", "Sets", "Intermediate", "How many proper subsets does a set with 4 elements have?", ["15", "16", "8", "4"], "15", "There are 2⁴ subsets, of which one is the set itself."),
 ("Mathematics", "Sets", "Hard", "If |A|=12, |B|=9 and |A∪B|=16, what is |A∩B|?", ["5", "3", "7", "21"], "5", "Use |A∪B| = |A| + |B| − |A∩B|."),
 ("Mathematics", "Trigonometry", "Easy", "What is sin 30°?", ["1/2", "1", "0", "√3/2"], "1/2", "Standard special-angle value."),
 ("Mathematics", "Trigonometry", "Intermediate", "What is sin² θ + cos² θ?", ["1", "0", "2", "tan θ"], "1", "Pythagorean identity."),
 ("Mathematics", "Trigonometry", "Hard", "For acute θ, if tan θ = 3/4, what is sin θ?", ["3/5", "4/5", "3/4", "5/3"], "3/5", "The opposite and adjacent sides are 3 and 4; hypotenuse is 5."),
 ("Physics", "Motion in a Straight Line", "Easy", "SI unit of acceleration?", ["m/s²", "m/s", "m", "kg·m/s"], "m/s²", "Acceleration is change of velocity per unit time."),
 ("Physics", "Motion in a Straight Line", "Intermediate", "A vehicle moves from rest at 2 m/s² for 4 seconds. Final speed?", ["8 m/s", "4 m/s", "2 m/s", "16 m/s"], "8 m/s", "v = u + at = 0 + 2×4."),
 ("Physics", "Motion in a Straight Line", "Hard", "A body starts from rest with constant acceleration and travels 18 m in 3 s. Acceleration?", ["4 m/s²", "2 m/s²", "6 m/s²", "9 m/s²"], "4 m/s²", "s=ut+½at², so 18=4.5a."),
 ("Chemistry", "Atomic Structure", "Easy", "The atomic number equals the number of:", ["Protons", "Neutrons", "Protons + neutrons", "Electron shells"], "Protons", "Atomic number is proton count."),
 ("Chemistry", "Atomic Structure", "Intermediate", "Maximum electrons in a shell with n=2?", ["8", "2", "18", "32"], "8", "Maximum occupancy is 2n²."),
 ("Chemistry", "Atomic Structure", "Hard", "How many orbitals are in the n=3 shell?", ["9", "3", "6", "18"], "9", "Number of orbitals in shell n is n²."),
 ("Biology", "Cell Structure", "Easy", "What organelle produces most ATP in aerobic eukaryotic cells?", ["Mitochondrion", "Ribosome", "Golgi apparatus", "Nucleus"], "Mitochondrion", "Mitochondria perform most aerobic cellular respiration."),
 ("Biology", "Cell Structure", "Intermediate", "Which structure is the main site of protein synthesis?", ["Ribosome", "Lysosome", "Centrosome", "Vacuole"], "Ribosome", "Ribosomes translate mRNA into polypeptides."),
 ("Biology", "Cell Structure", "Hard", "A cell has DNA and ribosomes but no membrane-bound nucleus. It is most likely:", ["Prokaryotic", "Plant eukaryotic", "Animal eukaryotic", "Fungal eukaryotic"], "Prokaryotic", "Prokaryotes do not have a membrane-bound nucleus."),
 ("English", "Grammar", "Easy", "Choose the grammatically correct sentence.", ["She has finished her work.", "She have finished her work.", "She finishing her work.", "She has finish her work."], "She has finished her work.", "Singular she uses has with past participle."),
 ("English", "Grammar", "Intermediate", "Choose the correct conditional: If I had known, I ___ earlier.", ["would have come", "will come", "would come", "come"], "would have come", "Third conditional uses would have + past participle."),
 ("English", "Grammar", "Hard", "Choose the sentence with correct subject–verb agreement.", ["Neither the teachers nor the principal is attending.", "Neither the teachers nor the principal are attending.", "Neither the teachers nor the principal be attending.", "Neither the teachers nor the principal were attending."], "Neither the teachers nor the principal is attending.", "In proximity agreement, the verb agrees with the nearer singular subject, principal."),
]

def question_bank(subject=None, topic=None, difficulty=None):
    result = []
    for i, (s, t, d, q, opts, answer, why) in enumerate(SEEDS):
        if subject and s.lower() != subject.lower(): continue
        if topic and t.lower() != topic.lower(): continue
        if difficulty and d != difficulty: continue
        result.append(dict(id=f"seed-{i}",subject=s,topic=t,difficulty=d,question=q,options=opts.copy(),answer=answer,explanation=why,source="Curated demo bank"))
    return result

def safe_quiz(bank, count, seed=None):
    rng=random.Random(seed)
    result=[dict(q) for q in rng.sample(bank, min(count,len(bank)))]
    for q in result:
        q['options']=rng.sample(q['options'],len(q['options']))
    return result

def clean_questions(data, subject, topic, difficulty, source="Local model"):
    arr = data.get('questions', []) if isinstance(data,dict) else []
    valid=[]
    for i,q in enumerate(arr):
        if not isinstance(q,dict): continue
        a=q.get('answer'); opts=q.get('options'); text=q.get('question')
        if not isinstance(text,str) or not isinstance(opts,list) or len(opts)!=4 or any(not isinstance(x,str) for x in opts) or len(set(opts))!=4 or a not in opts: continue
        valid.append(dict(id=str(uuid_hash(text)),subject=subject,topic=str(q.get('topic') or topic),difficulty=difficulty,question=text,options=opts,answer=a,explanation=str(q.get('explanation') or 'Verify with your source.'),source=source))
    if not valid: raise ValueError('No valid questions were returned')
    return valid

def uuid_hash(text): return hashlib.sha256(text.encode()).hexdigest()[:16]

def quadrant(accuracy, confidence):
    if accuracy >= .7 and confidence >= .67: return 'Mastery zone', 'Maintain with spaced review and harder questions'
    if accuracy < .7 and confidence >= .67: return 'Hidden weakness', 'Check confidently incorrect answers and rebuild misconceptions'
    if accuracy < .7: return 'Foundation gap', 'Relearn with worked examples and guided easier practice'
    return 'Confidence gap', 'Use repeated retrieval and low-stakes timed practice'

def score_quiz(quiz, responses, confidences):
    rows=[]
    for q, answer, c in zip(quiz, responses, confidences):
        rows.append(dict(question_id=q['id'],question=q['question'],subject=q['subject'],topic=q['topic'],difficulty=q['difficulty'],selected=answer,answer=q['answer'],correct=int(answer==q['answer']),confidence=int(c),explanation=q['explanation'],source=q['source'],source_url=q.get('source_url','')))
    return rows

def diagnostic(rows):
    if not rows: return []
    groups={}
    for r in rows: groups.setdefault((r['subject'],r['topic']),[]).append(r)
    out=[]
    for (subject,topic),items in groups.items():
        accuracy=sum(x['correct'] for x in items)/len(items)
        confidence=sum(x['confidence'] for x in items)/(3*len(items))
        zone,action=quadrant(accuracy,confidence)
        out.append(dict(subject=subject,topic=topic,attempted=len(items),correct=sum(x['correct'] for x in items),accuracy=round(100*accuracy,1),confidence=round(100*confidence,1),zone=zone,next_action=action))
    return sorted(out,key=lambda x:(x['accuracy'], -x['attempted']))

def schedule(topics,days,minutes_per_day, exam_name):
    topics=list(topics) or ['General revision']
    output=[]
    for d in range(days):
        topic=topics[d%len(topics)]
        activity=['Review fundamentals + 3 worked examples','Active recall + flashcards','Timed mixed practice + error log','Reattempt previously missed questions'][d%4]
        output.append(dict(day=d+1,date=(date.today()+timedelta(days=d)).isoformat(),exam=exam_name,topic=topic,minutes=minutes_per_day,activity=activity,completed=False))
    return output

def extract_candidates(text,limit=30):
    # Rule-based fallback for uploaded notes, no claim of original AI generation.
    lines=[re.sub(r'\s+',' ',x).strip(' •-*\t') for x in text.splitlines()]
    lines=[x for x in lines if 20<=len(x)<=280 and not x.lower().startswith(('http://','https://'))]
    seen=set();out=[]
    for x in lines:
        key=x.lower()
        if key in seen: continue
        seen.add(key)
        out.append(x)
        if len(out)>=limit: break
    return out


# ----------------------------------------------------------
# Kinematics question families: independently computed keys.
# Not generative AI, and not copied from search results.
# ----------------------------------------------------------
def is_straight_line_motion(subject, topic):
    text = (topic or '').lower()
    return (subject or '').lower() == 'physics' and any(
        phrase in text for phrase in (
            'straight line', 'rectilinear', '1d motion',
            'one dimensional motion', 'linear motion', 'kinematics',
            'motion in one dimension'
        )
    )


def kinematics_quiz(subject, topic, difficulty, count=10, exam='ISC Boards', grade='Class 11'):
    """Build 5-20 diverse parameterised, calculator-checked MCQs.

    Uses basic constant-acceleration kinematics and dimensions.
    Uses online reference links but no third-party AI or Google scraping.
    """
    import random
    rng = random.SystemRandom()
    count = max(5, min(20, int(count)))
    source_url = 'https://openstax.org/books/college-physics-2e/pages/2-5-motion-equations-for-constant-acceleration-in-one-dimension'
    # Each tuple: (concept, question, correct numeric, wrong numeric candidates, unit, explanation).
    # Fresh numbers are selected for every question.
    families=[]
    def add(concept, prompt, value, distractors, unit, reasoning):
        families.append((concept, prompt, value, distractors, unit, reasoning))

    a=rng.randint(2,6); t=rng.randint(3,9); u=rng.randint(2,12)
    add('Velocity and acceleration',f'A particle moves at {u} m/s and accelerates uniformly at {a} m/s² for {t} s. Find its final velocity.', u+a*t,[u+a*(t-1), a*t, u+2*a*t], 'm/s',f'v = u + at = {u} + {a} × {t} = {u+a*t} m/s.')
    a=rng.randint(2,6); t=rng.randint(2,8)
    add('Displacement',f'A body starts from rest and accelerates at {a} m/s² for {t} s. Find displacement.',a*t*t/2,[a*t*t,a*t, a*t*t/4],'m',f's = ut + ½at² = ½ × {a} × {t}² = {a*t*t/2:g} m.')
    u=rng.randint(6,18); v=u+rng.randint(4,18);t=rng.randint(2,8)
    add('Average velocity',f'A car increases its velocity uniformly from {u} m/s to {v} m/s. What is its average velocity over this interval?',(u+v)/2,[v-u, v, (v-u)/2],'m/s',f'With constant acceleration, average velocity = (u+v)/2 = ({u}+{v})/2.')
    u=rng.randint(3,12);v=u+rng.randint(10,25);t=rng.randint(2,8)
    add('Acceleration',f'An object changes velocity from {u} m/s to {v} m/s in {t} s at a constant rate. Find acceleration.',(v-u)/t,[(v+u)/t,(v-u)*t,v/t],'m/s²',f'a = (v-u)/t = ({v}-{u})/{t} = {(v-u)/t:g} m/s².')
    u=rng.randint(10,25); a=rng.randint(2,6)
    add('Stopping time',f'A vehicle moving at {u} m/s brakes with a constant retardation of {a} m/s². Find the stopping time.',u/a,[u*a,u/(2*a),2*u/a],'s',f'0 = u − at, so t = u/a = {u}/{a} = {u/a:g} s.')
    u=rng.randint(8,20); a=rng.randint(2,6)
    add('Stopping distance',f'A vehicle moving at {u} m/s decelerates uniformly at {a} m/s² until it stops. Find its stopping distance.',u*u/(2*a),[u/a,u*u/a,u*u/(4*a)],'m',f'0 = u² − 2as, so s = u²/(2a) = {u*u}/({2*a}) = {u*u/(2*a):g} m.')
    u=rng.randint(4,12);t=rng.randint(3,8)
    add('Uniform motion',f'A cyclist travels at a constant velocity of {u} m/s for {t} s. Find displacement.',u*t,[u+t,u*t/2,u*t*t],'m',f's = vt = {u} × {t} = {u*t} m.')
    a=rng.randint(2,7); t=rng.randint(3,8)
    add('Velocity-time graph',f'An object starts from rest. Its velocity increases linearly to {a*t} m/s in {t} s. Find displacement from the velocity-time graph.',a*t*t/2,[a*t*t,a*t,a*t*t/4],'m',f'Area of triangle under v–t graph = ½ × base × height = ½ × {t} × {a*t}.')
    u=rng.randint(2,10);a=rng.randint(2,6);t=rng.randint(3,8)
    add('Distance with acceleration',f'A particle has initial velocity {u} m/s and accelerates uniformly at {a} m/s² for {t} s in the same direction. Find displacement.',u*t+a*t*t/2,[u*t+a*t*t,u*t+a*t,u*t-a*t*t/2],'m',f's = ut + ½at² = {u}×{t} + ½×{a}×{t}².')
    u=rng.randint(2,10);a=rng.randint(2,6);s=rng.randint(8,30)
    val=u*u+2*a*s
    add('Velocity-displacement relation',f'A body starts at {u} m/s and accelerates uniformly at {a} m/s² over {s} m. What is the square of its final speed (v²)?',val,[u*u+a*s,u*u+4*a*s,2*a*s],'m²/s²',f'v² = u² + 2as = {u}² + 2×{a}×{s} = {val} m²/s².')
    # Extra independent variations for a 15-20 question test.
    for extra_i in range(10):
        a=rng.randint(2,8);t=3+extra_i;u=rng.randint(1,12)
        if len(families)%2:
            add('Uniform acceleration', f'An object accelerates uniformly from {u} m/s at {a} m/s² over {t} s. How much does its speed change?',a*t,[u+a*t,u*t,a*t*t/2],'m/s',f'Change in velocity = at = {a}×{t} = {a*t} m/s.')
        else:
            add('Average velocity',f'A body moves at {u} m/s initially and {u+a*t} m/s finally during {t} s of constant acceleration. Its average velocity is:',u+a*t/2,[u+a*t,u+a*t/4,a*t/2],'m/s',f'Average velocity = (u+v)/2 = ({u}+{u+a*t})/2.')
    rng.shuffle(families)
    output=[]
    for i,(concept,prompt,value,wrong,unit,explanation) in enumerate(families[:count]):
        # Round all displayed values identically and reject duplicate choices.
        values=[value]+wrong
        displayed=[f'{v:.2f}'.rstrip('0').rstrip('.') + ' ' + unit for v in values]
        if len(set(displayed))<4:
            # Deterministic fallback distractors, all distinct after rounding.
            step=max(1.0, abs(value)*0.2)
            displayed=[f'{v:.2f}'.rstrip('0').rstrip('.') + ' ' + unit for v in (value,value+step,value+2*step,value+3*step)]
        if len(set(displayed))<4:
            displayed=[f'{value + offset:.2f} {unit}' for offset in (0, 10, 20, 30)]
        answer=displayed[0]
        rng.shuffle(displayed)
        output.append(dict(id=uuid_hash(prompt),subject=subject,topic=concept,
            difficulty=difficulty,question=prompt,options=displayed,answer=answer,
            explanation=explanation,source='Original equation-based problem; OpenStax reference',
            source_url=source_url))
    return output
