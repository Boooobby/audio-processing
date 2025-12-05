import os
from pathlib import Path
from pydub import AudioSegment
import webbrowser

class AudioExporter:
    def __init__(self, output_dir="output_audio"):
        """
        初始化导出器
        :param output_dir: 最终成品存放的目录
        """
        self.output_dir = Path(output_dir)
        self._ensure_dir()

    def _ensure_dir(self):
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)

    def export_to_mp3(self, wav_path, bitrate="192k"):
        """
        将 WAV 转码为 MP3 (模拟 Web 下载用的最终格式)
        :param wav_path: 输入的 wav 路径
        :param bitrate: 比特率 (通信原理考点：压缩率与音质的权衡)
        :return: 导出的 mp3 绝对路径
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
        生成一个临时的 HTML 页面并在浏览器打开，
        模拟未来 Web 应用的前端播放效果。
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
        
        html_file = self.output_dir / "preview_player.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print("正在打开浏览器预览...")
        webbrowser.open(f"file://{html_file.absolute()}")