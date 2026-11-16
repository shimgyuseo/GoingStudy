"""나의 공부 성장 기록장 — 수행평가용 Streamlit 데모.
외부 저장소 없이 session_state만 사용합니다. 예시 기록은 모두 가상입니다.
새로고침/세션 종료 시 초기화될 수 있으며 다른 기기와 공유되지 않습니다.
선택적 Secrets: APP_URL, PARENT_DEMO_PIN (미설정 시 공개 시연 PIN 2468).
"""
import calendar
import copy
import hmac
import io
import time
import uuid
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
import streamlit as st
import qrcode

KST = ZoneInfo('Asia/Seoul')
UTC = timezone.utc
SUBJECTS = ['국어', '수학', '영어', '한국사', '사회', '과학', '기타']
REASONS = ['개념 부족', '관점·해석 오류', '계산 실수', '암기 부족', '시간 부족', '기타']
st.set_page_config(page_title='나의 공부 성장 기록장', page_icon='🌱', layout='centered')
st.markdown('''<style>
.block-container{max-width:760px;padding-top:1.1rem;padding-bottom:2rem}
.stApp{background:#f5faf8;color:#183e35}
h1{font-size:1.5rem!important} h2{font-size:1.15rem!important}
button{min-height:44px!important} [data-testid="stMetricValue"]{font-size:1.35rem}
[data-testid="stMetricLabel"]{font-size:.85rem}
div.stButton>button[kind="primary"]{background:#207862;border-color:#207862}
[data-testid="stExpander"]{background:white;border-radius:12px}
</style>''', unsafe_allow_html=True)

def now():
    return datetime.now(UTC)

def iso(t):
    return t.astimezone(UTC).isoformat()

def dt(s):
    return datetime.fromisoformat(s)

def today():
    return now().astimezone(KST).date()

def uid():
    return uuid.uuid4().hex

def fmt(seconds):
    s = max(0, int(seconds))
    return f'{s//3600:02}:{s%3600//60:02}:{s%60:02}'

def initial():
    return {'mode':'auto', 'cycle':uid(), 'active_day':None, 'segments':[],
            'notes':[], 'reviews':[], 'exams':[], 'stamps':{},
            'grades':[{'id':'baseline1','name':'1학기 평균 (약)','value':2.0,'date':None},
                      {'id':'baseline2','name':'중간고사 (약)','value':1.8,'date':None}],
            'target':None}

def seed_demo():
    data = initial()
    data['target'] = 1.5
    base = today()
    for i in range(6, -1, -1):
        day = base-timedelta(days=i)
        started = datetime.combine(day, datetime.min.time(), KST)+timedelta(hours=8)
        duration = 35 if i==0 else 50+i*10
        data['segments'].append({'id':uid(),'start':iso(started),'end':iso(started+timedelta(minutes=duration)),
            'mode':'auto','day':day.isoformat(),'cycle':'sample',
            'subject':['수학','영어','국어'][i%3], 'content':'[가상 예시] '+['함수 그래프와 오답 정리','영어 지문 근거 찾기','문학 작품 표현 분석'][i%3]})
        if i>0:
            data['stamps'][day.isoformat()]={'at':iso(started+timedelta(hours=1,minutes=duration))}
    examples = [
      ('수학','이차함수 최댓값','개념 부족','복습 필요','f(x)=-x²+4x+1의 최댓값을 구하시오.','f(x)=-(x-2)²+5이므로 최댓값은 5이다.','함숫값과 x좌표를 혼동했다.','완전제곱식과 꼭짓점의 관계가 부족했다.','유형 풀이 후 조건을 바꿔 보는 연습이 부족했다.'),
      ('영어','독해 지문 근거 찾기','관점·해석 오류','복습 필요','[가상 지문] Some students prefer silence. However, others learn better with quiet music. 글의 내용으로 알맞은 것은?','학생마다 선호하는 공부 환경이 다르다. however 뒤의 대조 내용까지 읽어야 한다.','앞 문장만 읽고 모든 학생이 조용한 환경을 선호한다고 일반화했다.','대조 연결어의 기능을 놓쳤다.','지문 속 근거 문장에 표시하는 연습이 부족했다.'),
      ('국어','직유법 구분','암기 부족','이해 완료','“구름 같은 솜사탕”에 사용된 표현법은?','직유법. “같은”을 사용해 솜사탕을 구름에 직접 빗댔다.','비유 대상과 표현을 충분히 확인하지 않았다.','직유법과 은유법을 구분하지 못했다.','정의만 외우고 예문 비교를 하지 않았다.'),
      ('수학','일차방정식 계산','계산 실수','이미 아는 유형','2x+3=9를 푸시오.','2x=6, x=3이다.','해당 없음','해당 없음','이항 후 부호를 점검하지 않았다.')]
    for i,(subject,title,reason,status,problem,answer,interpretation,concept,preparation) in enumerate(examples):
        nid=uid()
        created=(base-timedelta(days=i+1)).isoformat()
        data['notes'].append(dict(id=nid,source='학교 시험' if i%2==0 else '기출·시험 대비 문제',subject=subject,
            title='[가상 예시] '+title,problem=problem,answer=answer,interpretation=interpretation,concept=concept,
            preparation=preparation,reasons=[reason],extra='다음 복습에서 풀이 이유를 말로 설명해 보기.',status=status,
            created_day=created,created_at=iso(now())))
        if status=='이해 완료':
            data['reviews'].append(dict(id=uid(),note_id=nid,title='[가상 예시] '+title,subject=subject,
                day=base.isoformat(),at=iso(now()),result=status))
    for subject,days in [('수학',2),('영어',3),('국어',7)]:
        data['exams'].append(dict(id=uid(),subject=subject,name='[가상 예시] 시험',day=(base+timedelta(days=days)).isoformat()))
    data['grades'].append(dict(id=uid(),name='[가상 예시] 다음 시험 평균',value=1.6,date=(base-timedelta(days=1)).isoformat()))
    return data

def option(key, default=''):
    try:
        return st.secrets.get(key,default)
    except Exception:
        return default

class StorageError(Exception):
    pass

if 'demo_data' not in st.session_state:
    st.session_state.demo_data=seed_demo()

def load():
    return {'data':copy.deepcopy(st.session_state.demo_data)}

def mutate(fn, role='student'):
    if st.session_state.get('role')!=role:
        raise StorageError('이 작업을 수행할 권한이 없습니다.')
    data=copy.deepcopy(st.session_state.demo_data)
    fn(data)
    st.session_state.demo_data=data

def save(fn, role='student'):
    try:
        mutate(fn,role)
        st.rerun()
    except StorageError as e:
        st.error(str(e))

st.title('🌱 나의 공부 성장 기록장')
st.caption('수행평가용 데모 · [가상 예시]는 실제 공부 기록이 아닙니다.')
with st.expander('프로그램 목표·시연 범위'):
    st.write('가족의 기대에 부응하고자 성적을 향상하고, 공부하는 노력의 과정을 부모님과 공유합니다. 서울 소재 대학 진학을 목표로 오답 분석과 학습 습관을 개선합니다.')
    st.caption('특정 등급으로 대학 합격을 보장하지 않습니다. 이 시연 버전은 실제 다중 기기 공유·영구 저장·부모님 신원 인증을 제공하지 않습니다.')
st.info('기록은 현재 접속 세션에서만 유지됩니다. 새로고침·연결 종료 시 초기화될 수 있고, 다른 기기와는 공유되지 않습니다.')
if 'role' not in st.session_state:
    with st.form('login'):
        role_label=st.radio('접속 역할',['학생','부모님'],horizontal=True)
        pin=st.text_input('부모님 시연용 PIN (학생은 비워 두세요)',type='password',max_chars=128)
        if not option('PARENT_DEMO_PIN'):
            st.caption('공개 시연용 부모님 PIN: 2468 · 실제 보안 인증이 아닙니다.')
        submit=st.form_submit_button('시연 시작',use_container_width=True)
    if submit:
        if role_label=='학생':
            st.session_state.role='student'
            st.rerun()
        elif time.time()<st.session_state.get('login_after',0):
            st.warning('잠시 후 다시 시도해 주세요.')
        elif hmac.compare_digest(pin,str(option('PARENT_DEMO_PIN','2468'))):
            st.session_state.role='parent'
            st.rerun()
        else:
            st.session_state.login_after=time.time()+3
            st.error('PIN이 맞지 않습니다.')
    st.stop()
student = st.session_state.role == 'student'
with st.sidebar:
    st.write('학생 모드' if student else '부모님 확인 모드')
    st.caption('역할을 바꿔도 같은 세션의 시연 기록은 유지됩니다.')
    if st.button('학생·부모님 역할 전환'):
        del st.session_state['role']
        st.rerun()
    confirm_reset=st.checkbox('변경 내용을 버리고 가상 예시로 되돌리기')
    if st.button('시연 초기화',disabled=not confirm_reset):
        st.session_state.clear()
        st.rerun()
try:
    state = load()['data']
except StorageError as e:
    st.error(str(e))
    st.stop()

# 날짜 경계에서 자르는 계산은 저장된 시작·종료 시각을 기준으로 수행.
# 세션이 유지될 때 저장된 시각으로 계산하며, 영구 보존은 하지 않는다.
def portions(segment, at):
    start = dt(segment['start'])
    end = dt(segment['end']) if segment.get('end') else at
    if end <= start:
        return []
    if segment['mode'] == 'manual':
        return [(segment['day'], (end-start).total_seconds())]
    result = []
    while start < end:
        local = start.astimezone(KST)
        boundary = datetime.combine(local.date()+timedelta(days=1), datetime.min.time(), KST).astimezone(UTC)
        stop = min(end, boundary)
        result.append((local.date().isoformat(), (stop-start).total_seconds()))
        start = stop
    return result

def totals(data, at):
    result = {}
    for s in data['segments']:
        for day, seconds in portions(s, at):
            result[day] = result.get(day, 0) + seconds
    return result

def close_running(data, at):
    for s in data['segments']:
        if not s.get('end'):
            s['end'] = iso(max(dt(s['start']), at))

def studied_day(data):
    return data.get('active_day') if data['mode']=='manual' and data.get('active_day') else today().isoformat()

@st.fragment(run_every='5s')
def timer_panel():
    try:
        data = load()['data']
    except StorageError as e:
        st.error(str(e))
        return
    at = now()
    day = studied_day(data)
    total = totals(data, at).get(today().isoformat(), 0)
    elapsed = 0
    for s in data['segments']:
        if s['cycle'] == data['cycle']:
            elapsed += sum(sec for d,sec in portions(s, at) if data['mode']=='manual' or d==today().isoformat())
    running = any(not s.get('end') for s in data['segments'])
    st.metric('오늘의 공부 시간', fmt(total))
    st.caption(f'타이머 {fmt(elapsed)} · {"공부 중" if running else "정지"} · {"자동 마감" if data["mode"]=="auto" else "직접 마감 / 공부일 "+day}')
    if not student:
        return
    with st.expander('공부할 과목·내용', expanded=False):
        subject = st.selectbox('과목', SUBJECTS, key='timer_subject')
        content = st.text_input('간단한 학습 내용', max_chars=500, key='timer_content')
        st.caption('시작할 때 선택한 내용이 저장됩니다. 바꾸려면 일시정지 후 다시 시작하세요.')
    controls = st.columns(3 if data['mode']=='manual' else 2)
    a,b = controls[:2]
    if a.button('공부 시작', disabled=running, type='primary', use_container_width=True):
        sid, started = uid(), now()
        def start(d):
            if any(not s.get('end') for s in d['segments']):
                return
            day0 = d.get('active_day') or started.astimezone(KST).date().isoformat()
            d['active_day'] = day0
            d['segments'].append({'id':sid,'start':iso(started),'end':None,
                'mode':d['mode'],'day':day0,'cycle':d['cycle'],'subject':subject,'content':content.strip()})
        save(start)
    if b.button('일시정지', disabled=not running, use_container_width=True):
        ended = now()
        save(lambda d: close_running(d, ended))
    if data['mode']=='manual' and controls[2].button('오늘 공부 끝', use_container_width=True):
        ended, newcycle = now(), uid()
        def finish(d):
            close_running(d, ended)
            d['cycle'] = newcycle
            d['active_day'] = None
        save(finish)
    st.caption('표시는 약 5초마다 갱신됩니다. 연결 세션이 유지되는 동안 시작~정지 사이 시간을 계산합니다. 새로고침하면 초기화될 수 있습니다.')
timer_panel()

st.subheader('공부 달력')
month = st.date_input('월 선택', value=today().replace(day=1), label_visibility='collapsed')
at = now()
daily = totals(state, at)
weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
for col, label in zip(st.columns(7), ['월','화','수','목','금','토','일']):
    col.markdown(f'**{label}**')
for week in weeks:
    for col, day0 in zip(st.columns(7), week):
        key = day0.isoformat()
        seconds = daily.get(key, 0)
        label = f'{day0.day}\n{int(seconds)//3600}h{int(seconds)%3600//60:02}' if seconds else str(day0.day)
        if key in state['stamps']:
            label += ' ✓'
        if col.button(label, key='cal_'+key, disabled=day0.month!=month.month, use_container_width=True):
            st.session_state.selected_day = key
selected = st.session_state.get('selected_day', today().isoformat())
week_start = today()-timedelta(days=today().weekday())
week_days = [(week_start+timedelta(days=i)).isoformat() for i in range(7)]
stamp_count = sum(d in state['stamps'] for d in week_days)
week_seconds = sum(daily.get(d,0) for d in week_days)
review_count = sum(n['status']=='이해 완료' for n in state['notes'])
a,b,c = st.columns(3)
a.metric('이번 주 공부', fmt(week_seconds))
b.metric('이해 완료 오답', f'{review_count}개')
c.metric('이번 주 스탬프', f'{stamp_count}/7')
st.caption('월요일~일요일 · '+'  '.join(f'{label}{"✅" if d in state["stamps"] else "▫️"}' for label,d in zip('월화수목금토일',week_days)))
if stamp_count == 7:
    st.success('이번 주 용돈 조건 달성!')

with st.expander(f'📅 {selected} 상세 기록·부모님 확인'):
    st.write('누적 공부 시간: **'+fmt(daily.get(selected,0))+'**')
    found = False
    for s in state['segments']:
        sec = sum(t for d,t in portions(s,at) if d==selected)
        if sec>0:
            found = True
            st.write(f'• {s["subject"]} · {fmt(sec)} · {s["content"] or "내용 미입력"}')
    if not found:
        st.caption('공부 시간 기록이 없습니다.')
    for n in state['notes']:
        if n['created_day']==selected:
            st.write(f'✍️ 작성: {n["subject"]} / {n["title"]} · {n["status"]}')
    for r in state['reviews']:
        if r['day']==selected:
            st.write(f'🔁 복습: {r["subject"]} / {r["title"]} · {r["result"]}')
    stamp = state['stamps'].get(selected)
    if stamp:
        st.success('부모님 확인 완료 · '+dt(stamp['at']).astimezone(KST).strftime('%m/%d %H:%M'))
        st.caption('스탬프는 해당 시점의 확인 기록입니다. 이후 추가된 공부 내용까지 확인했다는 뜻은 아닙니다.')
    elif student:
        st.caption('부모님으로 로그인하면 확인 스탬프를 찍을 수 있습니다.')
    elif selected > today().isoformat():
        st.info('미래 날짜에는 스탬프를 찍을 수 없습니다.')
    else:
        confirmed = st.checkbox('위 날짜의 공부 시간·학습 내용·오답 기록을 확인했습니다.')
        if st.button('부모님 확인 스탬프', disabled=not confirmed, type='primary'):
            stamp_at = iso(now())
            def stamp_day(d):
                if selected not in d['stamps']:
                    d['stamps'][selected] = {'at':stamp_at}
            save(stamp_day, 'parent')

st.subheader('오답·시험 직전 복습')
upcoming = {}
for e in state['exams']:
    diff = (date.fromisoformat(e['day'])-today()).days
    if 0 <= diff <= 3:
        upcoming[e['subject']] = min(upcoming.get(e['subject'], date.max), date.fromisoformat(e['day']))
if upcoming:
    st.warning('3일 이내 시험: '+', '.join(f'{s} {d:%m/%d}' for s,d in upcoming.items()))
if 'cram' not in st.session_state:
    st.session_state.cram = False
if st.button('시험 직전 복습', use_container_width=True):
    st.session_state.cram = not st.session_state.cram
show_all = st.checkbox('이해 완료·이미 아는 유형도 보기', disabled=st.session_state.cram)
if st.session_state.cram:
    st.caption('시험 직전 복습 중: 모든 과목의 복습 필요 문제만 표시하며, 3일 이내 시험 과목이 우선입니다.')
filtered = [n for n in state['notes'] if n['status']=='복습 필요' or (show_all and not st.session_state.cram)]
filtered.sort(key=lambda n:(0 if n['subject'] in upcoming else 1, upcoming.get(n['subject'],date.max), n['created_day']))
st.caption(f'복습 필요 {sum(n["status"]=="복습 필요" for n in state["notes"])}개 · 이해 완료 {review_count}개')
if not filtered:
    st.info('표시할 오답이 없습니다. 새 오답을 작성하거나 완료 항목 보기를 켜 주세요.')
for n in filtered:
    with st.expander(f'{"🔥 " if n["subject"] in upcoming and n["status"]=="복습 필요" else ""}{n["subject"]} · {n["title"]} · {n["status"]}'):
        st.caption(n['source']+' · '+n['created_day']+' · '+', '.join(n['reasons']))
        for label,key in [('문제 내용','problem'),('정답 및 풀이','answer'),('문제를 잘못 해석한 부분','interpretation'),('개념이 부족했던 부분','concept'),('시험 준비에서 부족했던 점','preparation'),('원인 추가 설명','extra')]:
            st.text(label+'\n'+(n.get(key) or '없음'))
        if student:
            status = st.selectbox('학습 상태', ['복습 필요','이해 완료','이미 아는 유형'], index=['복습 필요','이해 완료','이미 아는 유형'].index(n['status']), key='status_'+n['id'])
            if st.button('복습 결과·상태 저장', key='review_'+n['id']):
                nid, result, rid, when = n['id'], status, uid(), iso(now())
                def review(d):
                    item = next(x for x in d['notes'] if x['id']==nid)
                    item['status'] = result
                    d['reviews'].append({'id':rid,'note_id':nid,'title':item['title'],'subject':item['subject'],
                        'day':studied_day(d),'at':when,'result':result})
                save(review)

if student:
    with st.expander('＋ 오답 작성'):
        with st.form('new_note', clear_on_submit=True):
            source = st.radio('문제 구분', ['학교 시험','기출·시험 대비 문제'], horizontal=True)
            subj = st.selectbox('오답 과목', SUBJECTS)
            title = st.text_input('문제명', max_chars=150)
            problem = st.text_area('문제 내용', max_chars=8000)
            answer = st.text_area('정답 및 풀이', max_chars=8000)
            interpretation = st.text_area('문제를 잘못 해석한 부분', help='해당 없으면 “해당 없음”이라고 적어 주세요.', max_chars=4000)
            concept = st.text_area('개념이 부족했던 부분', max_chars=4000)
            preparation = st.text_area('시험 준비에서 부족했던 점', max_chars=4000)
            reasons = st.multiselect('틀린 원인 (복수 선택)', REASONS)
            extra = st.text_area('원인 추가 설명', max_chars=4000)
            if st.form_submit_button('오답 저장', type='primary'):
                if not all(x.strip() for x in [title,problem,answer,interpretation,concept,preparation]) or not reasons:
                    st.error('문제명·문제·풀이·세 가지 분석과 틀린 원인을 모두 입력해 주세요. 해당 없는 분석에는 “해당 없음”이라고 적어 주세요.')
                else:
                    entry = dict(id=uid(),source=source,subject=subj,title=title.strip(),problem=problem.strip(),answer=answer.strip(),
                        interpretation=interpretation.strip(),concept=concept.strip(),preparation=preparation.strip(),reasons=reasons,extra=extra.strip(),status='복습 필요')
                    def add_note(d):
                        item = dict(entry, created_day=studied_day(d), created_at=iso(now()))
                        d['notes'].append(item)
                    save(add_note)

with st.expander('시험 일정·성적 변화'):
    for e in sorted(state['exams'], key=lambda x:x['day']):
        st.write(f'{e["day"]} · {e["subject"]} · {e["name"]}')
        if student and st.button('일정 삭제', key='del_exam_'+e['id']):
            eid = e['id']
            save(lambda d: d.update(exams=[x for x in d['exams'] if x['id']!=eid]))
    if student:
        with st.form('exam'):
            exam_subj = st.selectbox('시험 과목', SUBJECTS)
            exam_name = st.text_input('시험명', max_chars=150)
            exam_day = st.date_input('시험 날짜')
            if st.form_submit_button('시험 일정 등록'):
                eid = uid()
                if not exam_name.strip():
                    st.error('시험명을 입력해 주세요.')
                else:
                    save(lambda d:d['exams'].append({'id':eid,'subject':exam_subj,'name':exam_name.strip(),'day':exam_day.isoformat()}))
    st.markdown('**성적 성장 기록**')
    st.caption('초기 참고값은 1학기 평균 약 2.0, 중간고사 약 1.8입니다. 시험의 범위·난도·산출 방식이 다르면 직접 비교에 한계가 있습니다.')
    grades = [g for g in state['grades'] if not g.get('date')] + sorted([g for g in state['grades'] if g.get('date')],key=lambda g:g['date'])
    previous = None
    for g in grades:
        change = ''
        if previous is not None:
            delta = previous-g['value']
            change = f' · {abs(delta):.2f}등급 '+('향상' if delta>0 else '하락' if delta<0 else '유지')
        st.write(f'{g.get("date") or "참고"} / {g["name"]}: **{g["value"]:.2f}등급**{change}')
        previous = g['value']
    if state.get('target') is not None and previous is not None:
        gap = previous-state['target']
        st.write(f'목표 {state["target"]:.2f}등급 · '+(f'최근 기록에서 {gap:.2f}등급 향상 필요' if gap>0 else '최근 기록 기준 목표 범위 도달'))
    else:
        st.caption('설정에서 목표 등급을 직접 정해 주세요.')
    st.info('서울 소재 대학 진학을 위한 성장 참고 기록입니다. 특정 등급만으로 대학 합격이 보장되지 않으며 전형·교과·활동 등 여러 요소를 함께 살펴야 합니다.')
    if student:
        with st.form('grade'):
            grade_name = st.text_input('성적 기록명 (과목·평균 여부를 포함)', max_chars=150)
            grade_date = st.date_input('시험/성적 날짜')
            grade_value = st.number_input('등급 (작을수록 향상)', min_value=1.0,max_value=9.0,value=1.8,step=.1,format='%.2f')
            if st.form_submit_button('성적 추가'):
                gid = uid()
                if not grade_name.strip():
                    st.error('성적 기록명을 입력해 주세요.')
                else:
                    save(lambda d:d['grades'].append({'id':gid,'name':grade_name.strip(),'date':grade_date.isoformat(),'value':grade_value}))

with st.expander('설정·QR 접속'):
    if student:
        with st.form('settings'):
            target = st.number_input('목표 등급', min_value=1.0,max_value=9.0,value=float(state.get('target') or 1.5),step=.1,format='%.2f')
            mode_label = st.radio('하루 공부 마감 방식', ['자동 마감','직접 마감'],index=0 if state['mode']=='auto' else 1)
            st.caption('자동: 한국 시간 자정 기준으로 날짜별 분할. 직접: 오늘 공부 끝을 누를 때까지 시작한 공부일에 합산. 자동→직접은 일시정지 후, 직접→자동은 오늘 공부 끝을 누른 후 변경하세요. 기존 달력 기록은 유지됩니다.')
            if st.form_submit_button('설정 저장'):
                mode = 'auto' if mode_label=='자동 마감' else 'manual'
                def settings(d):
                    if mode!=d['mode']:
                        if any(not x.get('end') for x in d['segments']):
                            raise StorageError('마감 방식 변경 전 일시정지해 주세요. 직접 마감 중이면 오늘 공부 끝을 눌러 주세요.')
                        if d['mode']=='manual' and d.get('active_day'):
                            raise StorageError('직접 마감 중입니다. 오늘 공부 끝을 누른 후 변경해 주세요.')
                        d['cycle']=uid()
                        d['active_day']=None
                    d.update(mode=mode,target=target)
                save(settings)
    app_url = str(option('APP_URL','')).strip()
    app_url = st.text_input('배포된 앱 주소 (QR용)',value=app_url,placeholder='https://앱이름.streamlit.app').strip()
    if app_url.startswith('https://'):
        qr = qrcode.make(app_url)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        st.image(buffer.getvalue(), width=180)
        st.link_button('배포된 앱 열기', app_url)
        st.download_button('QR 이미지 다운로드', buffer.getvalue(), file_name='study-app-qr.png',mime='image/png')
        st.caption('QR에는 앱 주소만 들어갑니다. 비밀번호나 연결 정보는 포함되지 않습니다.')
    else:
        st.caption('배포 후 보안 설정의 APP_URL에 https://로 시작하는 실제 앱 주소를 넣으면 QR이 표시됩니다.')
    st.caption('수행평가용 임시 기록입니다. 학생·부모님 역할 전환은 같은 세션에서 시연하세요. 실제 다중 기기 공유·영구 저장·부모님 신원 인증은 제공하지 않습니다.')
