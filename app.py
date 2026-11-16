"""나의 공부 성장 기록장. Streamlit Community Cloud: app.py.
선택적 Secrets: PARENT_PIN, APP_URL. 데이터와 사진은 접속 세션에만 보관.
서로 다른 브라우저/기기는 독립 세션. 역할 전환은 데이터를 보존한다.
"""
import calendar
import hmac
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from html import escape
import streamlit as st
import streamlit.components.v1 as components
import qrcode

KST = ZoneInfo('Asia/Seoul')
UTC = timezone.utc
BASIC = ['수학', '국어', '영어', '사회', '과학', '한국사']
CAUSES = ['개념 부족', '관점·해석 오류', '계산 실수', '암기 부족', '시간 부족', '기타']
MENUS = [('home','성장기록'),('notes','오답노트'),('stamps','스탬프'),('settings','설정')]
st.set_page_config(page_title='나의 공부 성장 기록장', page_icon='📖', layout='centered')

def now():
    return datetime.now(UTC)

def today():
    return now().astimezone(KST).date()

def uid():
    return uuid.uuid4().hex

def iso(value):
    return value.astimezone(UTC).isoformat()

def fmt(value):
    sec = max(0, int(value))
    return f'{sec//3600:02}:{sec%3600//60:02}:{sec%60:02}'

def secret(key, default=''):
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default

def empty_data():
    return dict(subjects=BASIC.copy(), segments=[], notes=[], exams=[], reviews=[], stamps={},
                mode='auto', cutoff=0, active_day=None, cycle=uid(), target=None, grades=[])

if 'records' not in st.session_state:
    st.session_state.records = empty_data()
if 'screen' not in st.session_state:
    st.session_state.screen = 'home'
if st.session_state.screen in ('timer','calendar'):
    st.session_state.screen='home'
st.session_state.records.setdefault('cutoff',0)
if 'theme' not in st.session_state:
    st.session_state.theme = '기기 설정'

# Datetime helpers do not depend on UI. UTC timestamps, KST study-day boundaries.
def portions(segment, at):
    start = datetime.fromisoformat(segment['start'])
    end = datetime.fromisoformat(segment['end']) if segment['end'] else at
    if end <= start:
        return []
    if segment['mode'] == 'manual':
        return [(segment['day'], (end-start).total_seconds())]
    out = []
    cutoff = int(segment.get('cutoff', 0))
    while start < end:
        local = start.astimezone(KST)
        day = (local-timedelta(minutes=cutoff)).date()
        boundary = (datetime.combine(day+timedelta(days=1), datetime.min.time(), KST)+timedelta(minutes=cutoff)).astimezone(UTC)
        stop = min(end, boundary)
        out.append((day.isoformat(), (stop-start).total_seconds()))
        start = stop
    return out

def totals(data, at):
    out = {}
    for segment in data['segments']:
        for day, sec in portions(segment, at):
            out[day] = out.get(day, 0)+sec
    return out

def stop_timer(data, at):
    for segment in data['segments']:
        if not segment['end']:
            segment['end'] = iso(max(at, datetime.fromisoformat(segment['start'])))

def study_day(data, at=None):
    at = at or now()
    return (at.astimezone(KST)-timedelta(minutes=int(data.get('cutoff',0)))).date().isoformat()


def authorize(role='student'):
    return st.session_state.get('role') == role

def start_subject(data, subject, content, at):
    # A new study session replaces the finish/undo state.
    data.pop('finish_undo', None)
    stop_timer(data, at)
    data['segments'].append(dict(id=uid(), subject=subject, content=content, start=iso(at), end=None,
        day=study_day(data,at), mode='auto', cutoff=data.get('cutoff',0), cycle=data['cycle']))

def finish_day(data, at):
    stop_timer(data, at)
    data['finish_undo'] = dict(cycle=data['cycle'], day=study_day(data, at))
    data['active_day'] = None
    data['cycle'] = uid()

def undo_finish(data, at):
    saved = data.pop('finish_undo', None)
    if saved and saved['day'] == study_day(data, at):
        data['cycle'] = saved['cycle']
    # Keep the timer paused: time since finishing must not count as study.

def add_stamp(data, day, at):
    key = day.isoformat()
    if day <= at.astimezone(KST).date() and key not in data['stamps']:
        data['stamps'][key] = iso(at)

def rerun():
    st.rerun()

css = '''
:root{--bg:#fff;--fg:#101010;--accent:#bc4900;--line:#dedede;--soft:#f5f5f5;color-scheme:light}
@media(prefers-color-scheme:dark){:root{--bg:#111;--fg:#f5f5f5;--accent:#ff9b43;--line:#303030;--soft:#1c1c1c;color-scheme:dark}}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;color:var(--fg)!important}
[data-testid="stHeader"],[data-testid="stToolbar"],footer,[data-testid="stDecoration"]{display:none!important}
[data-testid="stMain"]{height:100dvh!important;overflow:hidden!important}
.block-container{max-width:560px!important;padding:12px 14px!important;height:100dvh;overflow:hidden}
h1{font-size:19px!important;line-height:1.4!important;padding:0!important;margin:0!important}
h2,h3{font-size:18px!important;line-height:1.4!important;padding:4px 0!important;margin:0!important}
p,label,span,[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"],[data-testid="stCaptionContainer"]{color:var(--fg)}
[data-testid="stCaptionContainer"]{opacity:.72}
[data-testid="stVerticalBlock"]{gap:9px!important}
.st-key-workspace{position:fixed!important;top:51px;bottom:calc(88px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);width:calc(100% - 28px);max-width:532px;overflow-y:auto!important;overflow-x:hidden!important;overscroll-behavior:contain;padding:4px 0 16px}
.st-key-bottomnav{position:fixed!important;bottom:calc(12px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);width:calc(100% - 24px);max-width:532px;z-index:100;background:var(--soft);border:1px solid var(--line);border-radius:32px;padding:6px!important}
.st-key-bottomnav [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:1px!important}
.st-key-bottomnav [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
.st-key-bottomnav button{height:53px!important;min-height:53px!important;border:0!important;border-radius:25px!important;background:transparent!important;padding:2px!important}
.st-key-bottomnav button p{font-size:11px!important;line-height:1.5!important;white-space:pre-line!important;font-weight:600}
.st-key-bottomnav button[kind="primary"]{background:var(--accent)!important;color:var(--bg)!important}
button{min-height:44px!important;border:1px solid var(--line)!important;border-radius:13px!important;background:var(--bg)!important;color:var(--fg)!important}
button p,button span{color:inherit!important}
button[kind="primary"]{background:var(--accent)!important;border-color:var(--accent)!important;color:var(--bg)!important}
button:disabled{opacity:.45}
input,textarea,[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"]>div,[role="option"],[role="listbox"],[data-baseweb="popover"]{background:var(--soft)!important;color:var(--fg)!important;-webkit-text-fill-color:var(--fg)!important}

[class*="st-key-editor_"]{display:block!important;min-height:108px!important;flex:0 0 auto!important;overflow:visible!important;padding:12px!important}
[class*="st-key-editor_"] textarea{min-height:68px!important}
/* Keep every editor visible inside the fixed-height mobile workspace. */
.st-key-workspace > div,.st-key-workspace [data-testid="stVerticalBlock"]{min-height:min-content!important}
.st-key-workspace [data-testid="stVerticalBlock"] > div{flex-shrink:0!important}
.st-key-workspace [data-testid="stTextArea"]{display:block!important;visibility:visible!important;min-height:78px!important;height:auto!important;overflow:visible!important;flex-shrink:0!important}
.st-key-workspace [data-testid="stTextArea"] textarea{display:block!important;visibility:visible!important;min-height:68px!important;height:68px!important;opacity:1!important;border:1px solid var(--line)!important;border-radius:10px!important;resize:vertical!important}

input::placeholder,textarea::placeholder{color:var(--fg)!important;opacity:.5}
[data-testid="stForm"],[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important}
[data-testid="stAlert"]{background:var(--soft)!important;color:var(--fg)!important;border:1px solid var(--line)}
[data-testid="stMetricValue"]{font-size:21px!important}
[data-testid="stMetricLabel"]{font-size:12px!important}
.st-key-role_student button,.st-key-role_parent button{aspect-ratio:1;min-height:0!important;width:100%;font-size:20px!important}
.st-key-role_student,.st-key-role_parent{max-width:190px;margin:auto}
.st-key-workspace [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:8px!important}
.st-key-workspace [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
.st-key-calgrid [data-testid="stHorizontalBlock"],.st-key-stampgrid [data-testid="stHorizontalBlock"],.subject-row [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:3px!important}
.st-key-calgrid [data-testid="stColumn"],.st-key-stampgrid [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
.st-key-calgrid button{min-height:44px!important;border:0!important;border-radius:8px!important;padding:1px!important}
.st-key-calgrid button p{font-size:11px!important;white-space:pre-line!important;line-height:1.25!important}
.st-key-stampgrid button{aspect-ratio:1;min-height:48px!important;border:1px dashed var(--accent)!important;border-radius:50%!important;padding:2px!important}
.st-key-stampgrid button p{font-size:12px!important;white-space:pre-line}
.st-key-stampgrid button:disabled{opacity:1!important}
.subject-name{font-size:19px;font-weight:600;margin:9px 0}

/* Dialog owns one native close button; prevent mobile control overlap. */
[role="dialog"]{width:calc(100vw - 32px)!important;max-width:480px!important;max-height:85dvh!important;overflow-y:auto!important;padding:24px!important;border-radius:20px!important;box-sizing:border-box!important}
[role="dialog"] [data-testid="stVerticalBlock"]{gap:18px!important}
[role="dialog"] h2{padding:0 48px 18px 0!important;line-height:1.5!important}
[role="dialog"] button{min-height:48px!important}
[role="dialog"] [data-testid="stCameraInput"]{margin-top:12px!important}
[role="dialog"] [data-testid="stCameraInput"] video{width:100%!important;height:auto!important;max-height:36dvh!important;object-fit:contain!important}
[role="dialog"] button[aria-label="Close"],[role="dialog"] button[aria-label="Close dialog"]{min-height:36px!important;width:36px!important;padding:4px!important}

.rule{border-top:1px solid var(--line);margin:8px 0}
'''
st.markdown('<style>'+css+'</style>', unsafe_allow_html=True)
if st.session_state.theme != '기기 설정':
    dark = st.session_state.theme=='어둡게'
    bg, fg, accent, line, soft = ('#111','#f5f5f5','#ff9b43','#303030','#1c1c1c') if dark else ('#fff','#101010','#bc4900','#dedede','#f5f5f5')
    st.markdown(f'<style>:root{{--bg:{bg}!important;--fg:{fg}!important;--accent:{accent}!important;--line:{line}!important;--soft:{soft}!important;color-scheme:{"dark" if dark else "light"}}}</style>', unsafe_allow_html=True)
st.title('자녀의 공부 성장 기록장' if st.session_state.get('role')=='parent' else '나의 공부 성장 기록장')

if 'role' not in st.session_state:
    with st.container(key='workspace'):
        st.write('공부의 과정과 성장을 함께 기록해요.')
        st.subheader('누가 사용하나요?')
        a,b=st.columns(2)
        with a:
            if st.button('학생',key='role_student',use_container_width=True):
                st.session_state.role='student'
                rerun()
        with b:
            if st.button('부모님',key='role_parent',use_container_width=True):
                st.session_state.parent_login=True
        if st.session_state.get('parent_login'):
            with st.form('parent_login_form'):
                pin=st.text_input('부모님 비밀번호',type='password')
                if not secret('PARENT_PIN'):
                    if st.session_state.get('parent_pin','2468')=='2468':
                        st.caption('기본 비밀번호 2468 · 설정에서 변경할 수 있습니다.')
                if st.form_submit_button('접속',type='primary',use_container_width=True):
                    expected=st.session_state.get('parent_pin',secret('PARENT_PIN','2468'))
                    if hmac.compare_digest(pin,expected):
                        st.session_state.role='parent'
                        rerun()
                    else:
                        st.error('비밀번호를 확인해 주세요.')
    st.stop()

student=authorize()
data=st.session_state.records
icons={'notes':'▤','home':'▦','stamps':'◎','settings':'⚙'}
with st.container(key='bottomnav'):
    for col,(key,label) in zip(st.columns(4),MENUS):
        if col.button(icons[key]+'\n'+label,key='nav_'+key,type='primary' if st.session_state.screen==key else 'secondary',use_container_width=True):
            st.session_state.screen=key
            rerun()

def day_details(data, day):
    key=day.isoformat()
    st.markdown(f'**{day:%m월 %d일} · {fmt(totals(data,now()).get(key,0))}**')
    any_record=False
    for seg in data['segments']:
        seconds=sum(sec for k,sec in portions(seg,now()) if k==key)
        if seconds>0:
            any_record=True
            st.write(f'{seg["subject"]} · {fmt(seconds)}'+(' · '+seg['content'] if seg['content'] else ''))
    if not any_record:
        st.caption('아직 공부 기록이 없습니다.')
    for note in data['notes']:
        if note['day']==key:
            st.write('작성한 오답 · '+note['subject']+' / '+note['title'])
    for review in data['reviews']:
        if review['day']==key:
            st.write('복습한 오답 · '+review['title']+' / '+review['result'])
    if key in data['stamps']:
        st.caption('부모님 확인 완료 · '+datetime.fromisoformat(data['stamps'][key]).astimezone(KST).strftime('%H:%M'))

def countdown(data):
    exam_day=data.get('exam_day')
    if not exam_day:
        return set()
    left=(date.fromisoformat(exam_day)-today()).days
    label='D-DAY' if left==0 else f'D-{left}' if left>0 else f'D+{-left}'
    st.write(f'시험 {label} · {exam_day}')
    if 0<=left<=3:
        st.write('자녀의 시험이 3일 이내입니다. 오답 복습 진행 상황을 확인해 주세요.' if st.session_state.get('role')=='parent' else '시험이 얼마 남지 않았어요. 틀렸던 오답노트를 집중 복습해 주세요!')
        return set(data['subjects'])
    return set()

# Browser timer updates every second. Python stores timestamps on every start/stop.
# The component only displays elapsed time; it is not the source of saved durations.
def clock(seconds, running):
    theme=st.session_state.theme
    html='''<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>
body{margin:0;background:transparent;color:#101010;font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif}
@media(prefers-color-scheme:dark){body{color:#f5f5f5}}
#clock{font-size:clamp(34px,10vw,48px);font-weight:700;text-align:center;letter-spacing:1px;font-variant-numeric:tabular-nums;padding:4px 0}
</style></head><body><div id="clock"></div><script>
const initial=SECONDS,active=RUNNING,started=performance.now();
function render(){const s=Math.max(0,Math.floor(initial+(active?(performance.now()-started)/1000:0)));document.getElementById('clock').textContent=[Math.floor(s/3600),Math.floor(s%3600/60),s%60].map(x=>String(x).padStart(2,'0')).join(':');}
render();setInterval(render,200);
</script></body></html>'''.replace('SECONDS',str(float(seconds))).replace('RUNNING','true' if running else 'false')
    if theme!='기기 설정':
        html=html.replace('</style>',f'body{{color:{"#f5f5f5" if theme=="어둡게" else "#101010"}!important}}</style>')
    components.html(html,height=70,scrolling=False)

def growth_summary(d):
    st.markdown('<div style="background:#ff9838;color:#111;padding:12px 14px;border-radius:10px;font-weight:700;margin-bottom:8px">'+('인서울을 위한 학습 성장 기록' if student else '자녀의 학습 과정과 성장 확인')+'</div>',unsafe_allow_html=True)
    latest=sorted(d['grades'],key=lambda g:g['day'])
    if latest:
        value=latest[-1]['value']
        message=f'최근 {value:.2f}등급'
        if len(latest)>1:
            delta=latest[-2]['value']-value
            message+=f' · {abs(delta):.2f}등급 '+('향상' if delta>0 else '하락' if delta<0 else '유지')
        if d['target']:
            message+=f' · 목표 {d["target"]:.2f}등급'
        st.write(message)
    elif d.get('target'):
        st.write(f'목표 {d["target"]:.2f}등급')
    else:
        st.caption('설정에서 목표 등급과 시험 성적을 기록해 주세요.' if student else '아직 등록된 성적이 없습니다.')
    need=sum(n['status']=='복습 필요' for n in d['notes'])
    done=sum(n['status']=='이해 완료' for n in d['notes'])
    st.write(f'복습 필요 {need}개 · 이해 완료 {done}개')
    countdown(d)

@st.fragment(run_every='1s')
def home_screen():
    data=st.session_state.records
    at=now()
    day=study_day(data,at)
    running=next((s for s in data['segments'] if not s['end']),None)
    elapsed=sum(sec for s in data['segments'] if s['cycle']==data['cycle'] for key,sec in portions(s,at) if key==day)
    growth_summary(data)
    st.caption(f'공부일 {day} · '+('공부 중' if running else '정지'))
    clock(elapsed if student else totals(data,at).get(day,0),bool(running))
    if student:
        if data.get('finish_undo', {}).get('day') != day:
            data.pop('finish_undo', None)
        controls=st.columns(3)
        if controls[0].button('시작',type='primary',disabled=bool(running),use_container_width=True):
            start_subject(data,st.session_state.get('home_subject',data['subjects'][0]),st.session_state.get('home_content','').strip(),now())
            rerun()
        if controls[1].button('일시정지',disabled=not running,use_container_width=True):
            stop_timer(data,now())
            rerun()
        if data.get('finish_undo'):
            if controls[2].button('실행 취소',use_container_width=True):
                undo_finish(data,now())
                rerun()
        elif controls[2].button('오늘 공부 끝',use_container_width=True):
            finish_day(data,now())
            rerun()
        a,b=st.columns([1,2])
        a.selectbox('과목',data['subjects'],key='home_subject',disabled=bool(running),label_visibility='collapsed')
        b.text_input('학습 내용',key='home_content',max_chars=500,placeholder='학습 내용',disabled=bool(running),label_visibility='collapsed')
    cutoff=data['cutoff']
    st.caption(f'매일 {cutoff//60:02}:{cutoff%60:02} 마감 · 공부일 누적 {fmt(totals(data,at).get(day,0))}')
    if 'month' not in st.session_state:
        st.session_state.month=today().replace(day=1)
    month=st.session_state.month
    left,middle,right=st.columns([1,4,1])
    if left.button('‹',key='prev_month',use_container_width=True):
        st.session_state.month=(month-timedelta(days=1)).replace(day=1)
        rerun()
    middle.subheader(f'{month.year}년 {month.month}월')
    if right.button('›',key='next_month',use_container_width=True):
        st.session_state.month=(month.replace(day=28)+timedelta(days=4)).replace(day=1)
        rerun()
    daily=totals(data,now())
    selected=st.session_state.get('selected_day',today().isoformat())
    with st.container(key='calgrid'):
        for col,label in zip(st.columns(7),'월화수목금토일'):
            col.caption(label)
        for week in calendar.Calendar(0).monthdatescalendar(month.year,month.month):
            for col,day in zip(st.columns(7),week):
                seconds=daily.get(day.isoformat(),0)
                text=str(day.day)
                key_day=day.isoformat()
                if data.get('exam_day')==key_day:
                    text+='\n시험'
                elif data.get('exam_day') and 1<=(date.fromisoformat(data['exam_day'])-day).days<=3:
                    text+='\n복습 D-'+str((date.fromisoformat(data['exam_day'])-day).days)
                for label,records in [('오답',data['notes']),('복습',data['reviews']),('성적',data['grades'])]:
                    count=sum(r['day']==key_day for r in records)
                    if count:
                        text+='\n'+label+' '+str(count)
                if seconds:
                    text+='\n'+fmt(seconds)
                if day.isoformat() in data['stamps']:
                    text+='\n◎'
                if col.button(text,key='day_'+day.isoformat(),disabled=day.month!=month.month,type='primary' if day.isoformat()==selected else 'secondary',use_container_width=True):
                    st.session_state.selected_day=day.isoformat()
                    rerun()
    st.markdown('<div class="rule"></div>',unsafe_allow_html=True)
    if student:
        with st.form('home_exam_date'):
            exam_day=st.date_input('시험 날짜',value=date.fromisoformat(data['exam_day']) if data.get('exam_day') else None)
            if st.form_submit_button('시험 날짜 저장',use_container_width=True):
                data['exam_day']=exam_day.isoformat() if exam_day else None
                rerun()
    day_details(data,date.fromisoformat(st.session_state.get('selected_day',today().isoformat())))
    if not student:
        selected=date.fromisoformat(st.session_state.get('selected_day',today().isoformat()))
        if st.button('이 공부일 확인 도장',disabled=selected>today() or selected.isoformat() in data['stamps'],use_container_width=True,type='primary'):
            add_stamp(data,selected,now())
            rerun()

for draft_key in ['note_other','text_problem','text_interpretation','text_preparation','note_concept','text_shortage','text_answer','note_number','note_causes']:
    if draft_key in st.session_state:
        st.session_state[draft_key]=st.session_state[draft_key]

with st.container(key='workspace'):
    screen=st.session_state.screen
    if screen=='home':
        home_screen()

    elif screen=='notes':
        st.subheader('오답노트' if student else '자녀의 오답·복습 기록')
        urgent=countdown(data)
        if student:
            # Both controls visible immediately: no hidden camera/upload chooser.
            @st.dialog('문제 사진')
            def photo_picker():
                st.caption('사진을 가져올 방법을 선택해 주세요.')
                for label,kind in zip(['사진 보관함','사진 찍기','파일 선택'],['library','camera','file']):
                    if st.button(label,key='photo_source_'+kind,use_container_width=True):
                        st.session_state.photo_source=kind
                source=st.session_state.get('photo_source')
                picked=None
                if source=='camera':
                    picked=st.camera_input('문제 사진 촬영',key='photo_capture_dialog')
                elif source in ('library','file'):
                    picked=st.file_uploader('사진 선택' if source=='library' else '이미지 파일 선택',type=['png','jpg','jpeg','webp'],key='photo_file_'+source)
                if picked is not None:
                    if picked.size>10*1024*1024:
                        st.error('사진은 10MB 이하로 선택해 주세요.')
                    else:
                        st.image(picked,use_container_width=True)
                        if st.button('이 사진 사용',type='primary',use_container_width=True):
                            st.session_state.note_photo=picked.getvalue()
                            st.rerun()
            if st.button('문제 사진',key='open_problem_photo',use_container_width=True):
                st.session_state.photo_source=None
                photo_picker()
            if st.session_state.get('note_photo'):
                st.image(st.session_state.note_photo,width=160)
                if st.button('사진 삭제',key='remove_note_photo'):
                    st.session_state.pop('note_photo',None)
                    rerun()
            subj=st.selectbox('과목',data['subjects'],key='note_subject')
            source=st.selectbox('문제 구분',['학교 시험','기출·시험 대비 문제'],key='note_source')
            title=st.text_input('문제번호',max_chars=150,key='note_number')
            with st.container(border=True,key='editor_text_problem'):
                st.markdown('**문제 내용·메모**')
                problem=st.text_area('문제 내용·메모',key='text_problem',height=68,max_chars=8000,label_visibility='collapsed')
            with st.container(border=True,key='editor_text_interpretation'):
                st.markdown('**틀린 관점·해석의 오류**')
                interpretation=st.text_area('틀린 관점·해석의 오류',key='text_interpretation',height=68,max_chars=8000,placeholder='어떤 조건이나 표현을 잘못 해석했나요?',label_visibility='collapsed')
            with st.container(border=True,key='editor_text_preparation'):
                st.markdown('**학습·시험 준비에서 부족했던 점**')
                preparation=st.text_area('학습·시험 준비에서 부족했던 점',key='text_preparation',height=68,max_chars=8000,label_visibility='collapsed')
            concept=''
            shortage=''
            cause=st.multiselect('틀린 원인',CAUSES,key='note_causes')
            with st.container(border=True,key='editor_note_other'):
                st.markdown('**원인 추가 설명**')
                extra=st.text_area('원인 추가 설명',height=68,max_chars=8000,key='note_other',placeholder='기타를 선택했다면 구체적인 원인을 꼭 적어 주세요. 다른 원인도 자세히 설명할 수 있습니다.',label_visibility='collapsed')
            with st.container(border=True,key='editor_text_answer'):
                st.markdown('**정답 및 풀이·다음 대비 방법**')
                answer=st.text_area('정답 및 풀이·다음 대비 방법',key='text_answer',height=68,max_chars=8000,label_visibility='collapsed')
            record_date=st.date_input('기록 날짜',value=today(),key='note_record_date')
            if st.button('오답 저장',type='primary',use_container_width=True):
                photo=st.session_state.get('note_photo')
                if not title.strip() or not interpretation.strip() or not preparation.strip() or not answer.strip() or not cause:
                    st.error('문제번호·관점 오류·준비 부족·풀이와 틀린 원인을 작성해 주세요. ')
                elif '기타' in cause and not extra.strip():
                    st.error('기타 원인을 직접 작성해 주세요.')
                elif not problem.strip() and photo is None:
                    st.error('문제 사진이나 문제 내용를 넣어 주세요.')
                else:
                    data['notes'].append(dict(id=uid(),subject=subj,source=source,title=title.strip(),problem=problem.strip(),
                        interpretation=interpretation.strip(),preparation=preparation.strip(),concept=concept.strip(),shortage=shortage.strip(),causes=list(cause),
                        extra=extra.strip(),answer=answer.strip(),status='복습 필요',day=record_date.isoformat(),photo=photo))
                    st.session_state.pop('note_photo',None)
                    st.success('오답을 저장했습니다.')
        st.markdown('**복습 목록**')
        filter_name=st.selectbox('표시할 오답',['복습 필요','시험 직전 복습','전체 기록'],key='note_filter')
        notes=[n for n in data['notes'] if filter_name=='전체 기록' or n['status']=='복습 필요']
        if filter_name=='시험 직전 복습':
            notes=[n for n in notes if n['subject'] in urgent]
        notes.sort(key=lambda n:(n['subject'] not in urgent,n['day']))
        st.caption(f'복습 필요 {sum(n["status"]=="복습 필요" for n in data["notes"])}개 · 이해 완료 {sum(n["status"]=="이해 완료" for n in data["notes"])}개')
        if not notes:
            st.write('표시할 오답이 없습니다.')
        for note in notes:
            with st.container(border=True):
                st.markdown('**'+note['subject']+' · '+note['title']+'**')
                st.caption(note['source']+' · '+note['status']+' · '+note['day'])
                if note['photo']:
                    st.image(note['photo'],use_container_width=True)
                for label,key in [('문제 내용','problem'),('틀린 관점·해석의 오류','interpretation'),('학습·시험 대비 부족','preparation'),('부족했던 개념','concept'),('부족했던 점','shortage'),('원인 추가 설명','extra'),('정답 및 풀이','answer')]:
                    if note.get(key):
                        st.write(label+'\n\n'+note[key])
                st.caption('틀린 원인: '+', '.join(note['causes']))
                if student:
                    status=st.selectbox('복습 상태',['복습 필요','이해 완료','이미 아는 유형'],index=['복습 필요','이해 완료','이미 아는 유형'].index(note['status']),key='status_'+note['id'])
                    if st.button('복습 결과 저장',key='save_'+note['id'],use_container_width=True):
                        note['status']=status
                        data['reviews'].append(dict(id=uid(),note_id=note['id'],title=note['title'],day=study_day(data),result=status))
                        rerun()

    elif screen=='stamps':
        st.subheader('이번 주 확인 도장' if student else '자녀의 주간 학습 확인')
        monday=today()-timedelta(days=today().weekday())
        days=[monday+timedelta(days=i) for i in range(7)]
        count=sum(day.isoformat() in data['stamps'] for day in days)
        st.write(f'월요일부터 일요일까지 · {count}/7')
        with st.container(key='stampgrid'):
            for col,day,label in zip(st.columns(7),days,'월화수목금토일'):
                stamped=day.isoformat() in data['stamps']
                if col.button(('◎ 완료' if stamped else '도장 찍기' if not student else '도장 자리')+'\n'+label+' '+str(day.day),key='stamp_slot_'+str(day),use_container_width=True,type='primary' if stamped else 'secondary',disabled=student or stamped or day>today()):
                    add_stamp(data,day,now())
                    st.session_state.stamp_day=day
                    rerun()
        if count==7:
            st.write('이번 주 용돈 조건 달성!' if student else '이번 주 7일 확인 완료 · 용돈 약속을 확인해 주세요.')
        selected=st.date_input('확인할 공부일',value=today(),max_value=today(),key='stamp_day_picker')
        day_details(data,selected)
        if not student:
            if st.button('이 날짜에 도장 찍기',type='primary',disabled=selected.isoformat() in data['stamps'],use_container_width=True):
                add_stamp(data,selected,now())
                rerun()
        else:
            st.caption('부모님이 확인하면 도장이 표시됩니다.')

        st.markdown('<div style="border:1px solid #ff9838;border-radius:10px;padding:12px;text-align:center;font-weight:700">'+('도장 모아서 용돈 받기!!!' if student else '자녀의 노력을 확인하고 응원 도장을 찍어 주세요!')+'</div>',unsafe_allow_html=True)

    elif screen=='settings':
        st.subheader('설정' if student else '보호자 설정·자녀 성적 확인')
        theme=st.selectbox('화면 테마',['기기 설정','밝게','어둡게'],index=['기기 설정','밝게','어둡게'].index(st.session_state.theme))
        if theme!=st.session_state.theme:
            st.session_state.theme=theme
            rerun()
        if st.button('학생·부모님 전환',use_container_width=True):
            st.session_state.pop('role',None)
            st.session_state.pop('parent_login',None)
            rerun()
        if student:
            with st.form('add_subject',clear_on_submit=True):
                new_subject=st.text_input('과목 추가',max_chars=30)
                if st.form_submit_button('과목 추가',use_container_width=True):
                    if new_subject.strip() and new_subject.strip() not in data['subjects']:
                        data['subjects'].append(new_subject.strip())
                        rerun()
            with st.form('day_mode'):
                minutes=int(data.get('cutoff',0))
                cutoff_time=st.time_input('하루 공부 마감 기준 시각 (한국 시간)',value=datetime.min.time().replace(hour=minutes//60,minute=minutes%60),step=timedelta(minutes=1))
                st.caption('기본 00:00. 02:00으로 바꾸면 00:00~01:59 공부는 전날에 합산하고 02:00부터 새 공부일로 계산합니다. 오늘 공부 끝을 누르면 달력 기록은 유지되고 타이머만 초기화됩니다. 실행 취소로 직전 누적 시간을 복원할 수 있습니다. 이미 기록된 시간은 기존 기준을 유지합니다.')
                if st.form_submit_button('기준 시각 저장',use_container_width=True):
                    new_cutoff=cutoff_time.hour*60+cutoff_time.minute
                    if new_cutoff!=data['cutoff']:
                        if any(not seg['end'] for seg in data['segments']):
                            st.error('기준 시각을 바꾸기 전에 공부를 일시정지해 주세요.')
                        else:
                            data.update(cutoff=new_cutoff,mode='auto',active_day=None,cycle=uid())
                            rerun()
            st.caption('성적은 5등급제 기준입니다. 평균 등급은 소수점으로 입력할 수 있습니다.')
            with st.form('goal'):
                target=st.text_input('목표 등급',value=str(data['target']) if data['target'] else '',placeholder='예: 1.5')
                if st.form_submit_button('목표 저장',use_container_width=True):
                    try:
                        value=float(target.strip())
                        if not 1<=value<=5:
                            raise ValueError
                        data['target']=value
                        rerun()
                    except ValueError:
                        st.error('목표 등급은 1~5 사이 숫자로 입력해 주세요. 예: 1.5')
            with st.form('grade',clear_on_submit=True):
                grade=st.text_input('등급',placeholder='예: 1.8')
                if st.form_submit_button('성적 추가',use_container_width=True):
                    try:
                        value=float(grade.strip())
                        if not 1<=value<=5:
                            raise ValueError
                        data['grades'].append(dict(id=uid(),name='성적',day=today().isoformat(),value=value))
                        rerun()
                    except ValueError:
                        st.error('1~5 사이의 등급을 입력해 주세요.')
        else:
            with st.form('parent_password'):
                new_pin=st.text_input('새 부모님 비밀번호',type='password')
                if st.form_submit_button('비밀번호 변경',use_container_width=True):
                    if len(new_pin)>=4:
                        st.session_state.parent_pin=new_pin
                        st.success('변경했습니다.')
                    else:
                        st.error('4자 이상 입력해 주세요.')
        if data['target']:
            st.write(f'목표 {data["target"]:.2f}등급')
        previous=None
        for g in sorted(data['grades'],key=lambda x:x['day']):
            change=''
            if previous is not None:
                delta=previous-g['value']
                change=f' · {abs(delta):.2f}등급 '+('향상' if delta>0 else '하락' if delta<0 else '유지')
            st.write(f'{g["day"]} {g["name"]} · {g["value"]:.2f}등급'+change)
            previous=g['value']
        if previous is not None and data['target']:
            gap=previous-data['target']
            st.write(f'목표까지 {gap:.2f}등급 향상 필요' if gap>0 else '최근 기록 기준 목표 범위 도달')
        app_url=st.text_input('QR 접속 주소',value=secret('APP_URL'),placeholder='https://앱이름.streamlit.app')
        if app_url.startswith('https://'):
            buf=io.BytesIO()
            qrcode.make(app_url).save(buf,format='PNG')
            st.image(buf.getvalue(),width=160)
            st.download_button('QR 다운로드',buf.getvalue(),file_name='study-qr.png',mime='image/png')
