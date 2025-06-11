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
root.geometry("800x480")  # 크기를 실제 AVN 화면 크기로 조정

# 배경 이미지 추가
background_image = Image.open("./avn.jpg")
background_image = background_image.resize((800, 480), Image.Resampling.LANCZOS)
background_photo = ImageTk.PhotoImage(background_image)

background_label = tk.Label(root, image=background_photo)
background_label.place(x=0, y=0, relwidth=1, relheight=1)

# 현재 파일 재생 상태 표시
current_file_label = tk.Label(root, text="재생 중인 파일 없음", font=("Helvetica", 14), fg="white", bg="black")
current_file_label.place(x=50, y=30)  # AVN 화면 위쪽에 표시

# Progressbar 추가 (재생 진행 상태)
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.place(x=50, y=400, width=700)

# MP3 파일 선택 버튼
file_button = tk.Button(root, text="MP3 파일 선택", font=("Helvetica", 12), command=choose_file, height=2, width=15, bg='gray', fg='white')
file_button.place(x=50, y=350)

# 디렉터리 선택 버튼 추가
dir_button = tk.Button(root, text="디렉터리 선택", font=("Helvetica", 12), command=choose_directory, height=2, width=15, bg='gray', fg='white')
dir_button.place(x=250, y=350)  # 파일 선택 버튼 옆에 배치

# Play 버튼 추가
play_button = tk.Button(root, text="Play", font=("Helvetica", 12), command=play_action, height=2, width=10, bg='green', fg='white')
play_button.place(x=450, y=350)

# Stop 버튼 추가
stop_button = tk.Button(root, text="Stop", font=("Helvetica", 12), command=stop_playback, height=2, width=10, bg='red', fg='white')
stop_button.place(x=570, y=350)

# 로그 출력 (GUI 스타일)
log_text = tk.Text(root, height=5, width=60, bg='black', fg='white', font=("Helvetica", 10))
log_text.place(x=50, y=250)

root.mainloop()

# UART 종료
if uart:
    uart.close()

# pygame 종료
pygame.quit()

