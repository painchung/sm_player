import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk  # for handling the background image
import threading
import serial  # UART 통신을 위한 모듈
import pygame  # MP3 재생을 위한 모듈

# UART 설정
log_method = "uart"  # "uart" 또는 "console" 설정 가능
uart_port = '/dev/ttyUSB0'  # 사용할 UART 포트
baud_rate = 115200  # UART 속도 설정

# pygame 초기화
pygame.init()
pygame.mixer.init()

# 재생 제어 변수
is_playing = False
stop_requested = False
current_thread = None
selected_path = None  # 선택된 파일 또는 디렉토리 경로
path_type = None  # 'file' 또는 'directory'

# UART 포트를 초기화
uart = None
if log_method == "uart":
    try:
        uart = serial.Serial(uart_port, baud_rate)
        print(f"시리얼 포트 {uart_port} 연결 성공")
    except serial.SerialException as e:
        print(f"UART 연결 실패: {e}")
        log_method = "console"  # 실패 시 로그를 콘솔로 출력

# 로그 메시지를 UART 및 콘솔과 GUI에 모두 출력하는 함수
def log_message(message):
    # GUI 로그 출력
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)

    # UART 또는 콘솔로 로그 출력
    if log_method == "uart" and uart:
        uart.write((message + "\n").encode())  # UART로 메시지 전송
    elif log_method == "console":
        print(message)  # 콘솔로 메시지 출력

def play_mp3(filename):
    global is_playing, stop_requested
    try:
        is_playing = True
        # 파일 재생 시작 로그 출력 - 상대 경로 사용
        relative_path = os.path.relpath(filename)
        log_message(f"Playing:{os.path.basename(filename)}")
        log_message(f"{relative_path}-Start")

        current_file_label.config(text=f"Playing: {os.path.basename(filename)}")
        root.update_idletasks()

        # MP3 파일 로드 및 재생
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # 재생 진행 상태 표시
        while pygame.mixer.music.get_busy() and not stop_requested:
            # 재생 위치 비율 계산 (0-1)
            pos = pygame.mixer.music.get_pos()
            if pos > 0:
                # 간단한 진행률 표시 (시간 기반)
                progress_var.set(min(100, (pos / 1000) * 10))  # 임시 진행률
            root.update_idletasks()
            pygame.time.wait(100)  # 100ms 대기

        # 정지 요청이 있었다면 음악 정지
        if stop_requested:
            pygame.mixer.music.stop()
            log_message(f"{relative_path}-Stopped")
        else:
            # 파일 재생 종료 로그 출력
            log_message(f"{relative_path}-End")

        current_file_label.config(text="No file playing")
        progress_var.set(0)
        is_playing = False

    except Exception as e:
        log_message(f"An error occurred: {str(e)}")
        is_playing = False

def play_directory(directory):
    global stop_requested
    # MP3 파일 찾기
    mp3_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(".mp3"):
            mp3_files.append(filename)

    # 총 MP3 파일 개수 출력
    log_message(f"총 {len(mp3_files)}개의 MP3 파일을 찾았습니다.")
    log_message("")

    # 정렬된 순서로 재생
    for filename in sorted(mp3_files):
        if stop_requested:
            break
        full_path = os.path.join(directory, filename)
        play_mp3(full_path)

def choose_file():
    global selected_path, path_type
    file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
    if file_path:
        selected_path = file_path
        path_type = 'file'
        log_message(f"파일 선택됨: {os.path.basename(file_path)}")

def choose_directory():
    global selected_path, path_type
    directory_path = filedialog.askdirectory()
    if directory_path:
        selected_path = directory_path
        path_type = 'directory'
        # MP3 파일 개수 확인
        mp3_count = len([f for f in os.listdir(directory_path) if f.lower().endswith('.mp3')])
        log_message(f"디렉토리 선택됨: {os.path.basename(directory_path)} ({mp3_count}개 MP3 파일)")

def play_action():
    """Play 버튼 동작 - 선택된 파일이나 디렉토리 재생"""
    global current_thread, stop_requested, selected_path, path_type
    if not is_playing:
        stop_requested = False

        # 선택된 경로가 있으면 재생
        if selected_path:
            if current_thread and current_thread.is_alive():
                stop_playback()

            if path_type == 'file':
                current_thread = threading.Thread(target=play_mp3, args=(selected_path,))
            elif path_type == 'directory':
                current_thread = threading.Thread(target=play_directory, args=(selected_path,))

            if current_thread:
                current_thread.start()
        else:
            # 선택된 경로가 없으면 기본 mp3 폴더 재생
            if os.path.exists("mp3"):
                if current_thread and current_thread.is_alive():
                    stop_playback()
                current_thread = threading.Thread(target=play_directory, args=("mp3",))
                current_thread.start()
            else:
                log_message("재생할 파일이나 디렉토리를 먼저 선택하세요.")

def stop_playback():
    """Stop 버튼 동작 - 재생 중지"""
    global stop_requested
    stop_requested = True
    pygame.mixer.music.stop()
    log_message("재생이 중지되었습니다.")

# Initialize GUI
root = tk.Tk()
root.title("SM Player")
root.geometry("900x600")
root.minsize(600, 400)

# 배경 이미지 처리
try:
    # 배경 이미지 로드
    bg_image = Image.open("./avn.jpg")

    # 창 크기 변경 시 배경 이미지 크기 조정 함수
    def resize_background(event=None):
        global bg_photo
        # 현재 창 크기에 맞춰 이미지 크기 조정
        resized_image = bg_image.resize((event.width, event.height), Image.Resampling.LANCZOS)
        bg_photo = ImageTk.PhotoImage(resized_image)
        bg_label.configure(image=bg_photo)
        bg_label.image = bg_photo

    # 배경 이미지 레이블
    bg_label = tk.Label(root)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    # 초기 배경 이미지 설정
    initial_bg = bg_image.resize((900, 600), Image.Resampling.LANCZOS)
    bg_photo = ImageTk.PhotoImage(initial_bg)
    bg_label.configure(image=bg_photo)

    # 창 크기 변경 이벤트 바인딩
    root.bind('<Configure>', resize_background)

    has_background = True
except:
    has_background = False
    root.configure(bg='#1e1e1e')

# 메인 컨테이너 프레임 (반투명 배경)
main_frame = tk.Frame(root, bg='#1e1e1e' if not has_background else '#000000')
if has_background:
    main_frame.configure(bg='black')
    # 프레임을 약간 투명하게 만들기 위해 배경색 설정
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
else:
    main_frame.pack(fill=tk.BOTH, expand=True)

# 상단 헤더 프레임 (반투명)
header_frame = tk.Frame(main_frame, bg='#2d2d2d', height=80)
header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
header_frame.pack_propagate(False)
if has_background:
    header_frame.configure(bg='#000000', highlightbackground='#00ff00', highlightthickness=1)

# 타이틀
title_label = tk.Label(header_frame, text="SM Music Player", font=("Helvetica", 24, "bold"),
                      fg="#00ff00", bg='#000000' if has_background else '#2d2d2d')
title_label.pack(pady=20)

# 현재 재생 상태 표시 프레임
status_frame = tk.Frame(main_frame, bg='#2d2d2d', height=60)
status_frame.pack(fill=tk.X, padx=10, pady=5)
status_frame.pack_propagate(False)
if has_background:
    status_frame.configure(bg='#000000', highlightbackground='#00ff00', highlightthickness=1)

current_file_label = tk.Label(status_frame, text="재생 중인 파일 없음", font=("Helvetica", 14),
                             fg="#00ff00", bg='#000000' if has_background else '#2d2d2d')
current_file_label.pack(pady=15)

# 진행률 표시 프레임
progress_frame = tk.Frame(main_frame, bg='#000000' if has_background else '#1e1e1e')
progress_frame.pack(fill=tk.X, padx=20, pady=10)

progress_var = tk.DoubleVar()
style = ttk.Style()
style.theme_use('clam')
style.configure("TProgressbar",
                background='#00ff00',
                troughcolor='#2d2d2d',
                bordercolor='#1e1e1e',
                lightcolor='#00ff00',
                darkcolor='#00ff00')

progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, style="TProgressbar")
progress_bar.pack(fill=tk.X, pady=5)

# 컨트롤 버튼 프레임
control_frame = tk.Frame(main_frame, bg='#000000' if has_background else '#1e1e1e')
control_frame.pack(pady=20)

# 버튼 스타일 설정
button_style = {
    'font': ("Helvetica", 11, "bold"),
    'height': 2,
    'width': 12,
    'relief': tk.FLAT,
    'cursor': 'hand2'
}

# 버튼들
file_button = tk.Button(control_frame, text="🎵 파일 선택",
                       command=choose_file, bg='#3a3a3a', fg='white',
                       activebackground='#4a4a4a', **button_style)
file_button.grid(row=0, column=0, padx=5, pady=5)

dir_button = tk.Button(control_frame, text="📁 폴더 선택",
                      command=choose_directory, bg='#3a3a3a', fg='white',
                      activebackground='#4a4a4a', **button_style)
dir_button.grid(row=0, column=1, padx=5, pady=5)

play_button = tk.Button(control_frame, text="▶ 재생",
                       command=play_action, bg='#00a652', fg='white',
                       activebackground='#00c652', **button_style)
play_button.grid(row=0, column=2, padx=5, pady=5)

stop_button = tk.Button(control_frame, text="■ 정지",
                       command=stop_playback, bg='#dc3545', fg='white',
                       activebackground='#fc3545', **button_style)
stop_button.grid(row=0, column=3, padx=5, pady=5)

# 로그 출력 프레임
log_frame = tk.Frame(main_frame, bg='#2d2d2d')
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
if has_background:
    log_frame.configure(bg='#000000', highlightbackground='#00ff00', highlightthickness=1)

# 로그 타이틀
log_title = tk.Label(log_frame, text="로그", font=("Helvetica", 12, "bold"),
                    fg="#00ff00", bg='#000000' if has_background else '#2d2d2d')
log_title.pack(anchor=tk.W, padx=10, pady=(10, 5))

# 로그 텍스트 위젯과 스크롤바
log_text_frame = tk.Frame(log_frame, bg='#000000' if has_background else '#2d2d2d')
log_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

log_scrollbar = tk.Scrollbar(log_text_frame)
log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

log_text = tk.Text(log_text_frame, height=8, bg='#0a0a0a', fg='#00ff00',
                  font=("Consolas", 10), wrap=tk.WORD,
                  yscrollcommand=log_scrollbar.set)
log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

log_scrollbar.config(command=log_text.yview)

root.mainloop()

# UART 종료
if uart:
    uart.close()

# pygame 종료
pygame.quit()
