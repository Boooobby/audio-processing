import os
from pathlib import Path
from pydub import AudioSegment
import webbrowser

class AudioExporter:
    def __init__(self, output_dir="output_audio"):
        """
        初始化导出器
        """
        self.output_dir = Path(output_dir)
        self._ensure_dir()

    def _ensure_dir(self):
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)

    def export_to_mp3(self, wav_path, bitrate="192k"):
        """
        将 WAV 转码为 MP3 (模拟 Web 下载用的最终格式)
        """
        wav_path = Path(wav_path)
        if not wav_path.exists():
            raise FileNotFoundError(f"找不到要导出的文件: {wav_path}")

        print(f"正在进行 MP3 编码 (比特率 {bitrate})...")
        audio = AudioSegment.from_wav(str(wav_path))
        output_filename = f"{wav_path.stem}_processed.mp3"
        output_path = self.output_dir / output_filename
        audio.export(str(output_path), format="mp3", bitrate=bitrate)
        return str(output_path.absolute())

    def regex_browser_playback(self, audio_path):
        """
        生成一个 HTML 页面并在浏览器打开
        """
        audio_path = Path(audio_path).absolute().as_uri()
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8"> 
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>通信原理音频处理 - 预览</title>
            <style>
                body {{ 
                    font-family: 'Helvetica Neue', Arial, sans-serif; 
                    padding: 40px; 
                    background: #f5f5f7; 
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                }}
                .player-card {{ 
                    background: white; 
                    padding: 40px; 
                    border-radius: 20px; 
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1); 
                    text-align: center;
                    max-width: 500px;
                    width: 100%;
                }}
                h2 {{ color: #1d1d1f; margin-bottom: 10px; }}
                p {{ color: #86868b; font-size: 0.9em; word-break: break-all; margin-bottom: 30px; }}
                audio {{ width: 100%; outline: none; }}
            </style>
        </head>
        <body>
            <div class="player-card">
                <h2>🎵 处理完成</h2>
                <p>文件路径: <br>{audio_path}</p>
                <audio controls autoplay>
                    <source src="{audio_path}" type="audio/mpeg">
                    您的浏览器不支持音频元素。
                </audio>
            </div>
        </body>
        </html>
        """

    def generate_visualizer_html(self, audio_path):
        """
        生成一个包含实时频谱可视化的 HTML 播放器
        """
        # 获取文件名用于标题
        filename = os.path.basename(audio_path)
        
        # HTML 模板字符串 (包含 CSS 和 JS)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Audio Spectrum Processor | {filename}</title>
            <style>
                :root {{
                    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --glass-bg: rgba(255, 255, 255, 0.1);
                    --glass-border: rgba(255, 255, 255, 0.2);
                    --text-color: #ffffff;
                }}

                body {{
                    margin: 0;
                    padding: 0;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background: var(--bg-gradient);
                    background-size: 200% 200%;
                    animation: gradient-anim 15s ease infinite;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    color: var(--text-color);
                    overflow: hidden;
                }}

                @keyframes gradient-anim {{
                    0% {{ background-position: 0% 50%; }}
                    50% {{ background-position: 100% 50%; }}
                    100% {{ background-position: 0% 50%; }}
                }}

                .container {{
                    position: relative;
                    width: 90%;
                    max-width: 1000px;
                    background: var(--glass-bg);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border-radius: 24px;
                    border: 1px solid var(--glass-border);
                    padding: 40px;
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}

                h1 {{
                    font-weight: 200;
                    letter-spacing: 2px;
                    margin-bottom: 10px;
                    font-size: 1.5rem;
                    opacity: 0.9;
                }}
                
                .file-name {{
                    font-weight: 500;
                    opacity: 0.7;
                    margin-bottom: 30px;
                    font-size: 0.9rem;
                    background: rgba(0,0,0,0.2);
                    padding: 5px 15px;
                    border-radius: 50px;
                }}

                canvas {{
                    width: 100%;
                    height: 300px;
                    border-radius: 12px;
                    /* 给 Canvas 一个轻微的内阴影，增加层次感 */
                    background: rgba(0, 0, 0, 0.2); 
                }}

                audio {{
                    margin-top: 30px;
                    width: 100%;
                    outline: none;
                    border-radius: 50px;
                }}
                
                /* 简单美化原生 Audio 控件 (仅限 Webkit 内核) */
                audio::-webkit-media-controls-enclosure {{
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 50px;
                }}
                audio::-webkit-media-controls-play-button,
                audio::-webkit-media-controls-mute-button {{
                    background-color: rgba(255,255,255,0.8);
                    border-radius: 50%;
                }}

                .tip {{
                    margin-top: 15px;
                    font-size: 0.75rem;
                    opacity: 0.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Audio DSP Result</h1>
                <div class="file-name">{filename}</div>
                
                <canvas id="visualizer"></canvas>
                
                <audio id="audioPlayer" src="{filename}" controls crossorigin="anonymous"></audio>
                
                <div class="tip">Analysis requires playback to start</div>
            </div>

            <script>
                const audio = document.getElementById('audioPlayer');
                const canvas = document.getElementById('visualizer');
                const ctx = canvas.getContext('2d');
                
                // 自适应 Canvas 分辨率 (HiDPI / Retina 屏优化)
                function resizeCanvas() {{
                    const dpr = window.devicePixelRatio || 1;
                    const rect = canvas.getBoundingClientRect();
                    canvas.width = rect.width * dpr;
                    canvas.height = rect.height * dpr;
                    ctx.scale(dpr, dpr);
                }}
                window.addEventListener('resize', resizeCanvas);
                // 初始化调用一次
                setTimeout(resizeCanvas, 100);

                let audioContext, analyser, source;
                let isInitialized = false;

                audio.addEventListener('play', () => {{
                    if (!isInitialized) {{
                        initAudio();
                        isInitialized = true;
                        resizeCanvas(); // 确保播放时尺寸正确
                    }}
                    if (audioContext && audioContext.state === 'suspended') {{
                        audioContext.resume();
                    }}
                }});

                function initAudio() {{
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    audioContext = new AudioContext();

                    source = audioContext.createMediaElementSource(audio);
                    analyser = audioContext.createAnalyser();
                    
                    // 下面两个参数决定了柱状图的平滑度和数量
                    analyser.fftSize = 512; 
                    analyser.smoothingTimeConstant = 0.8; // 让跳动更柔和，不那么神经质

                    source.connect(analyser);
                    analyser.connect(audioContext.destination);

                    draw();
                }}

                function draw() {{
                    requestAnimationFrame(draw);

                    const bufferLength = analyser.frequencyBinCount;
                    const dataArray = new Uint8Array(bufferLength);
                    analyser.getByteFrequencyData(dataArray);

                    // 获取逻辑尺寸而非物理像素尺寸
                    const width = canvas.width / (window.devicePixelRatio || 1);
                    const height = canvas.height / (window.devicePixelRatio || 1);

                    ctx.clearRect(0, 0, width, height);

                    // 柱子数量稍微少取一点（只取前 2/3 的低-中频），因为高频通常能量很低，也是空的
                    const displayBins = Math.floor(bufferLength * 0.7); 
                    const barWidth = (width / displayBins) * 0.8; // 0.8 系数为了留出间隙
                    let x = 0;

                    for (let i = 0; i < displayBins; i++) {{
                        const value = dataArray[i];
                        // 映射高度：让低音量也能稍微显示一点
                        const percent = value / 255;
                        const barHeight = percent * height * 0.9; 

                        // 现代渐变色填充：从下到上 (青 -> 紫 -> 粉)
                        const gradient = ctx.createLinearGradient(0, height, 0, height - barHeight);
                        gradient.addColorStop(0, "rgba(66, 220, 244, 0.8)");
                        gradient.addColorStop(0.5, "rgba(224, 62, 224, 0.8)");
                        gradient.addColorStop(1, "rgba(255, 115, 0, 0.9)");

                        ctx.fillStyle = gradient;
                        
                        // 圆角柱子 (画圆角矩形稍微复杂一点，这里用普通矩形 + 圆形顶部模拟)
                        // 简单起见，直接画矩形，或者可以用 roundRect (新API)
                        if (ctx.roundRect) {{
                            ctx.beginPath();
                            ctx.roundRect(x, height - barHeight, barWidth, barHeight, [5, 5, 0, 0]);
                            ctx.fill();
                        }} else {{
                            ctx.fillRect(x, height - barHeight, barWidth, barHeight);
                        }}

                        // 间距计算：均分剩余空间
                        x += (width / displayBins);
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        # 确定 HTML 文件路径（和 MP3 放在一起）
        output_dir = os.path.dirname(audio_path)
        html_path = os.path.join(output_dir, "player_viz.html")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"可视化界面已生成: {html_path}")
        return html_path

    def browser_playback(self, file_path):
        """更新后的播放方法，先生成 HTML 再打开 HTML"""
        # 1. 生成带频谱的 HTML
        html_path = self.generate_visualizer_html(file_path)
        # 2. 调用浏览器打开本地 HTML 文件 -> file:///D:/.../player_viz.html
        webbrowser.open(f"file://{os.path.abspath(html_path)}")
        
        html_file = self.output_dir / "preview_player.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print("正在打开浏览器预览...")
        webbrowser.open(f"file://{html_file.absolute()}")