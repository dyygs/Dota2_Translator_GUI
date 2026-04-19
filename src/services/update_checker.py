import os
import sys
import json
import urllib.request
import ssl
import threading
import hashlib

from src.core.version import VERSION

GITEE_API_URL = "https://gitee.com/api/v5/repos/{owner}/{repo}/releases/latest"
GITEE_RAW_URL = "https://gitee.com/{owner}/{repo}/raw/master/version.txt"

GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/{owner}/{repo}/main/version.txt"

GITHUB_PROXIES = [
    "https://gh-proxy.com/",
    "https://githubproxy.cc/",
]

DEFAULT_UPDATE_SOURCES = [
    {"type": "gitee", "enabled": True},
    {"type": "github", "enabled": True},
]

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def parse_version(v):
    try:
        parts = v.lstrip('v').split('.')
        return tuple(int(p) for p in parts)
    except:
        return (0,)

def check_update_gitee(owner, repo, current_version=None, callback=None):
    """
    检查Gitee上的更新 (API方式)
    """
    if current_version is None:
        current_version = VERSION
    
    result = {
        'has_update': False,
        'latest_version': current_version,
        'download_url': '',
        'download_filename': '',
        'release_notes': '',
        'error': None,
        'source': 'gitee'
    }
    
    def do_check():
        try:
            url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/releases/latest"
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Dota2Translator'})
            
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', current_version)
            result['latest_version'] = latest_version
            
            if parse_version(latest_version) > parse_version(current_version):
                result['has_update'] = True
                
                assets = data.get('assets', [])
                if assets:
                    for asset in assets:
                        name = asset.get('name', '')
                        if name.endswith('.exe'):
                            result['download_url'] = asset.get('browser_download_url', '')
                            result['download_filename'] = name
                            break
                
                if not result['download_url'] and assets:
                    result['download_url'] = assets[0].get('browser_download_url', '')
                    result['download_filename'] = assets[0].get('name', 'update.exe')
                
                result['release_notes'] = data.get('body', '')
            
        except Exception as e:
            result['error'] = str(e)
        
        if callback:
            callback(result)
    
    if callback:
        threading.Thread(target=do_check, daemon=True).start()
    else:
        do_check()
    
    return result

def check_update_gitee_simple(owner, repo, current_version=None):
    """
    检查Gitee上的更新 (简单方式 - 使用version.txt)
    """
    if current_version is None:
        current_version = VERSION
    
    result = {
        'has_update': False,
        'latest_version': current_version,
        'download_url': '',
        'download_filename': '',
        'release_notes': '',
        'error': None,
        'source': 'gitee'
    }
    
    try:
        url = f"https://gitee.com/{owner}/{repo}/raw/master/version.txt"
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Dota2Translator'})
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            content = response.read().decode('utf-8')
        
        lines = content.strip().split('\n')
        latest_version = current_version
        download_url = ''
        release_notes = []
        
        in_release_notes = False
        for line in lines:
            line = line.strip()
            if line.startswith('VERSION='):
                latest_version = line.split('=', 1)[1].strip()
            elif line.startswith('DOWNLOAD_URL='):
                download_url = line.split('=', 1)[1].strip()
            elif line.startswith('RELEASE_NOTES='):
                in_release_notes = True
                note = line.split('=', 1)[1].strip()
                if note:
                    release_notes.append(note)
            elif in_release_notes and line:
                release_notes.append(line)
        
        result['latest_version'] = latest_version
        result['download_url'] = download_url
        
        if download_url:
            result['download_filename'] = download_url.split('/')[-1]
        
        result['release_notes'] = '\n'.join(release_notes)
        
        if parse_version(latest_version) > parse_version(current_version):
            result['has_update'] = True
            
    except Exception as e:
        result['error'] = str(e)
    
    return result

def check_update_github(owner, repo, current_version=None):
    """
    检查GitHub上的更新 (API方式，支持国内代理)
    
    Args:
        owner: GitHub用户名
        repo: GitHub仓库名
        current_version: 当前版本号
    
    Returns:
        dict: 更新检查结果
    """
    if current_version is None:
        current_version = VERSION
    
    result = {
        'has_update': False,
        'latest_version': current_version,
        'download_url': '',
        'download_filename': '',
        'release_notes': '',
        'error': None,
        'source': 'github'
    }
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    
    urls_to_try = [proxy + api_url for proxy in GITHUB_PROXIES]
    urls_to_try.append(api_url)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for url in urls_to_try:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Dota2Translator'})
            
            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', current_version)
            result['latest_version'] = latest_version
            
            if parse_version(latest_version) > parse_version(current_version):
                result['has_update'] = True
                
                assets = data.get('assets', [])
                if assets:
                    for asset in assets:
                        name = asset.get('name', '')
                        if name.endswith('.exe'):
                            download_url = asset.get('browser_download_url', '')
                            if url != api_url:
                                for proxy in GITHUB_PROXIES:
                                    if url.startswith(proxy):
                                        result['download_url'] = proxy + download_url
                                        break
                            else:
                                result['download_url'] = download_url
                            result['download_filename'] = name
                            break
                
                if not result['download_url'] and assets:
                    download_url = assets[0].get('browser_download_url', '')
                    if url != api_url:
                        result['download_url'] = GITHUB_PROXIES[0] + download_url
                    else:
                        result['download_url'] = download_url
                    result['download_filename'] = assets[0].get('name', 'update.exe')
                
                result['release_notes'] = data.get('body', '')
            
            result['error'] = None
            return result
            
        except Exception as e:
            result['error'] = str(e)
            continue
    
    return result

def check_update_github_simple(owner, repo, current_version=None):
    """
    检查GitHub上的更新 (使用version.json，支持国内代理)
    """
    if current_version is None:
        current_version = VERSION
    
    result = {
        'has_update': False,
        'latest_version': current_version,
        'download_url': '',
        'download_filename': '',
        'release_notes': '',
        'sha256': '',
        'size': 0,
        'force_update': False,
        'min_version': '',
        'update_type': 'full',
        'error': None,
        'source': 'github'
    }
    
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/version.json"
    
    urls_to_try = [proxy + raw_url for proxy in GITHUB_PROXIES]
    urls_to_try.append(raw_url)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for url in urls_to_try:
        try:
            print(f"[更新检查] 尝试获取 version.json: {url[:50]}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Dota2Translator'})
            
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                content = response.read().decode('utf-8')
            
            data = json.loads(content)
            
            latest_version = data.get('version', current_version)
            download_url = data.get('download_url', '')
            release_notes = data.get('release_notes', '')
            sha256 = data.get('sha256', '')
            size = data.get('size', 0)
            force_update = data.get('force_update', False)
            min_version = data.get('min_version', '')
            update_type = data.get('update_type', 'full')
            
            result['latest_version'] = latest_version
            result['download_url'] = download_url
            result['sha256'] = sha256
            result['size'] = size
            result['release_notes'] = release_notes
            result['force_update'] = force_update
            result['min_version'] = min_version
            result['update_type'] = update_type
            
            if download_url:
                result['download_filename'] = download_url.split('/')[-1]
            
            if parse_version(latest_version) > parse_version(current_version):
                result['has_update'] = True
            
            result['error'] = None
            print(f"[更新检查] 解析成功: version={latest_version}, has_update={result['has_update']}, force_update={force_update}")
            return result
            
        except Exception as e:
            print(f"[更新检查] 获取失败: {e}")
            result['error'] = str(e)
            continue
    
    return result

def check_update_multi_source(config, current_version=None, callback=None):
    """
    多源更新检查 - 按顺序尝试多个源，找到第一个可用的
    
    Args:
        config: 配置字典，包含:
            - github_owner: GitHub用户名
            - github_repo: GitHub仓库名
            - gitee_owner: Gitee用户名
            - gitee_repo: Gitee仓库名
        current_version: 当前版本号
        callback: 回调函数
    
    Returns:
        dict: 第一个成功检测到更新源的检查结果
    """
    if current_version is None:
        current_version = VERSION
    
    github_owner = config.get('github_owner', '')
    github_repo = config.get('github_repo', '')
    gitee_owner = config.get('gitee_owner', '')
    gitee_repo = config.get('gitee_repo', '')
    
    sources = []
    
    if gitee_owner and gitee_repo:
        sources.append(('gitee', {'owner': gitee_owner, 'repo': gitee_repo}))
    
    if github_owner and github_repo:
        sources.append(('github', {'owner': github_owner, 'repo': github_repo}))
    
    def do_check():
        checked_sources = []
        
        for source_type, source_info in sources:
            try:
                print(f"[更新检查] 尝试 {source_type} 源...")
                if source_type == 'gitee':
                    result = check_update_gitee_simple(source_info['owner'], source_info['repo'], current_version)
                elif source_type == 'github':
                    result = check_update_github_simple(source_info['owner'], source_info['repo'], current_version)
                
                print(f"[更新检查] {source_type} 结果: error={result.get('error')}, has_update={result.get('has_update')}")
                
                checked_sources.append({
                    'type': source_type,
                    'result': result
                })
                
                if result['error'] is None:
                    if callback:
                        callback(result)
                    return result
                    
            except Exception as e:
                print(f"[更新检查] {source_type} 异常: {e}")
                checked_sources.append({
                    'type': source_type,
                    'error': str(e)
                })
                continue
        
        result = {
            'has_update': False,
            'latest_version': current_version,
            'download_url': '',
            'download_filename': '',
            'release_notes': '',
            'error': '所有更新源均不可用',
            'checked_sources': checked_sources
        }
        
        if callback:
            callback(result)
        return result
    
    if callback:
        threading.Thread(target=do_check, daemon=True).start()
    else:
        return do_check()

def calculate_sha256(file_path):
    """
    计算文件的SHA256值
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: SHA256哈希值（小写），文件不存在返回空字符串
    """
    if not os.path.exists(file_path):
        return ''
    
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest().lower()
    except Exception as e:
        print(f"[更新检查] 计算SHA256失败: {e}")
        return ''

def verify_file_sha256(file_path, expected_sha256):
    """
    校验文件SHA256值
    
    Args:
        file_path: 文件路径
        expected_sha256: 预期的SHA256值
    
    Returns:
        bool: 校验是否通过
    """
    if not expected_sha256:
        return True
    
    actual_sha256 = calculate_sha256(file_path)
    return actual_sha256 == expected_sha256.lower()

def download_update(url, dest_path, progress_callback=None, expected_sha256=None):
    """
    下载更新文件（支持代理和SHA256校验）
    
    Args:
        url: 下载链接
        dest_path: 保存路径
        progress_callback: 进度回调 (downloaded, total, current_url)
        expected_sha256: 预期的SHA256值
    
    Returns:
        dict: {'success': bool, 'error': str, 'verified': bool}
    """
    result = {'success': False, 'error': None, 'verified': False}
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        from src.environment.python_installer import PythonInstaller
        log_file = os.path.join(PythonInstaller.get_data_dir(), "download.log")
    except Exception:
        log_file = os.path.join(os.path.expanduser("~"), "Dota2Translator", "download.log")
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def write_log(msg):
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{msg}\n")
        except Exception:
            pass
    
    log = write_log
    
    urls_to_try = [proxy + url for proxy in GITHUB_PROXIES]
    urls_to_try.append(url)
    
    log(f"[更新下载] 原始URL: {url}")
    log(f"[更新下载] 将尝试 {len(urls_to_try)} 个URL")
    
    timeout = 30
    
    for i, try_url in enumerate(urls_to_try):
        try:
            log(f"[更新下载] [{i+1}/{len(urls_to_try)}] 尝试: {try_url[:80]}...")
            
            req = urllib.request.Request(try_url, headers={'User-Agent': 'Dota2Translator'})
            
            log(f"[更新下载] 正在连接(超时{timeout}秒)...")
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                log(f"[更新下载] 连接成功! 文件大小: {total_size} bytes ({total_size/1024/1024:.2f} MB)")
                
                if progress_callback:
                    progress_callback(0, max(total_size, 1), try_url)
                
                with open(dest_path, 'wb') as f:
                    last_report = 0
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            if total_size > 0:
                                progress_callback(downloaded, total_size, try_url)
                            else:
                                if downloaded - last_report > 1024 * 1024:
                                    progress_callback(downloaded, downloaded, try_url)
                                    last_report = downloaded
            
            log(f"[更新下载] 下载完成! 总计: {downloaded} bytes")
            result['success'] = True
            
            if expected_sha256:
                log(f"[更新下载] 正在校验SHA256...")
                if verify_file_sha256(dest_path, expected_sha256):
                    result['verified'] = True
                    log(f"[更新下载] SHA256校验通过")
                else:
                    result['error'] = 'SHA256校验失败'
                    result['verified'] = False
                    log(f"[更新下载] SHA256校验失败")
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
                    continue
            else:
                result['verified'] = True
            
            return result
        except Exception as e:
            log(f"[更新下载] 下载失败: {e}")
            result['error'] = str(e)
            continue
    
    return result

def create_update_script(current_exe, new_exe, restart=True):
    """
    创建更新批处理脚本
    
    Args:
        current_exe: 当前exe路径
        new_exe: 新exe路径
        restart: 是否重启
    
    Returns:
        str: 批处理脚本路径
    """
    import tempfile
    
    script_content = f'''@echo off
chcp 65001 >nul
echo 正在更新 Dota2Translator...
echo.

:wait
tasklist /FI "IMAGENAME eq {os.path.basename(current_exe)}" 2>NUL | find /I "{os.path.basename(current_exe)}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 >NUL
    goto wait
)

echo 正在替换文件...
move /Y "{new_exe}" "{current_exe}"

if exist "{new_exe}" (
    del /F /Q "{new_exe}"
)

echo 更新完成!
'''
    
    if restart:
        script_content += f'''
echo 正在启动新版本...
start "" "{current_exe}"
'''
    
    script_content += '''
timeout /t 2 >NUL
del /F /Q "%~f0"
exit
'''
    
    script_path = os.path.join(tempfile.gettempdir(), "dota2_translator_update.bat")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    return script_path

def perform_update(new_exe_path, current_exe_path, restart=True):
    """
    执行更新（创建批处理并退出程序）
    
    Args:
        new_exe_path: 新exe路径
        current_exe_path: 当前exe路径
        restart: 是否重启
    """
    script_path = create_update_script(current_exe_path, new_exe_path, restart)
    
    import subprocess
    subprocess.Popen(['cmd', '/c', script_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='更新检查工具')
    parser.add_argument('--github-owner', default='dyygs', help='GitHub用户名')
    parser.add_argument('--github-repo', default='Dota2_Translator_GUI', help='GitHub仓库名')
    parser.add_argument('--gitee-owner', default='', help='Gitee用户名')
    parser.add_argument('--gitee-repo', default='', help='Gitee仓库名')
    parser.add_argument('--version', default=VERSION, help='当前版本')
    
    args = parser.parse_args()
    
    config = {
        'github_owner': args.github_owner,
        'github_repo': args.github_repo,
        'gitee_owner': args.gitee_owner,
        'gitee_repo': args.gitee_repo,
    }
    
    result = check_update_multi_source(config, args.version)
    
    print(f"当前版本: {args.version}")
    print(f"最新版本: {result['latest_version']}")
    print(f"有更新: {result['has_update']}")
    print(f"下载链接: {result['download_url']}")
    print(f"来源: {result.get('source', 'unknown')}")
    if result['error']:
        print(f"错误: {result['error']}")
