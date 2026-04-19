import os
import sys
import json
import urllib.request
import ssl
import threading

from src.core.version import VERSION

GITEE_API_URL = "https://gitee.com/api/v5/repos/{owner}/{repo}/releases/latest"
GITEE_RAW_URL = "https://gitee.com/{owner}/{repo}/raw/master/version.txt"

GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/{owner}/{repo}/main/version.txt"

GITHUB_PROXIES = [
    "https://ghproxy.com/",
    "https://mirror.ghproxy.com/",
]

DEFAULT_UPDATE_SOURCES = [
    {"type": "gitee", "enabled": True},
    {"type": "github", "enabled": True},
    {"type": "huawei", "enabled": True, "url": ""},
]

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def parse_version(v):
    try:
        parts = v.lstrip('v').split('.')
        return tuple(int(p) for p in parts)
    except:
        return (0,)

def check_update_huawei(obs_url, current_version=None):
    """
    检查华为云OBS上的更新
    
    Args:
        obs_url: 华为云OBS的version.txt访问地址
        current_version: 当前版本号
    
    Returns:
        dict: {'has_update': bool, 'latest_version': str, 'download_url': str, 'error': str}
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
        'source': 'huawei'
    }
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(obs_url, headers={'User-Agent': 'Dota2Translator'})
        
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

def check_update_github(owner, repo, current_version=None, use_proxy=True):
    """
    检查GitHub上的更新 (API方式，支持国内代理)
    
    Args:
        owner: GitHub用户名
        repo: GitHub仓库名
        current_version: 当前版本号
        use_proxy: 是否使用代理（国内用户建议使用）
    
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
    
    urls_to_try = []
    if use_proxy:
        for proxy in GITHUB_PROXIES:
            urls_to_try.append(proxy + api_url)
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
                            if use_proxy:
                                for proxy in GITHUB_PROXIES:
                                    urls_to_try_dl = proxy + download_url
                            else:
                                result['download_url'] = download_url
                            result['download_filename'] = name
                            break
                
                if not result['download_url'] and assets:
                    download_url = assets[0].get('browser_download_url', '')
                    if use_proxy and download_url:
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

def check_update_github_simple(owner, repo, current_version=None, use_proxy=True):
    """
    检查GitHub上的更新 (简单方式 - 使用version.txt)
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
    
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/version.txt"
    
    urls_to_try = []
    if use_proxy:
        for proxy in GITHUB_PROXIES:
            urls_to_try.append(proxy + raw_url)
    urls_to_try.append(raw_url)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for url in urls_to_try:
        try:
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
            
            result['error'] = None
            return result
            
        except Exception as e:
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
            - huawei_obs_url: 华为云OBS的version.txt地址
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
    huawei_url = config.get('huawei_obs_url', '')
    
    sources = []
    
    if gitee_owner and gitee_repo:
        sources.append(('gitee', {'owner': gitee_owner, 'repo': gitee_repo}))
    
    if github_owner and github_repo:
        sources.append(('github', {'owner': github_owner, 'repo': github_repo}))
    
    if huawei_url:
        sources.append(('huawei', huawei_url))
    
    def do_check():
        checked_sources = []
        
        for source_type, source_info in sources:
            try:
                if source_type == 'gitee':
                    result = check_update_gitee_simple(source_info['owner'], source_info['repo'], current_version)
                elif source_type == 'github':
                    result = check_update_github_simple(source_info['owner'], source_info['repo'], current_version)
                elif source_type == 'huawei':
                    result = check_update_huawei(source_info, current_version)
                
                checked_sources.append({
                    'type': source_type,
                    'result': result
                })
                
                if result['error'] is None:
                    if callback:
                        callback(result)
                    return result
                    
            except Exception as e:
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

def download_update(url, dest_path, progress_callback=None):
    """
    下载更新文件
    
    Args:
        url: 下载链接
        dest_path: 保存路径
        progress_callback: 进度回调 (downloaded, total)
    
    Returns:
        bool: 是否成功
    """
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Dota2Translator'})
        
        with urllib.request.urlopen(req, context=ctx) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)
        
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='更新检查工具')
    parser.add_argument('--github-owner', default='dyygs', help='GitHub用户名')
    parser.add_argument('--github-repo', default='Dota2_Translator_GUI', help='GitHub仓库名')
    parser.add_argument('--gitee-owner', default='', help='Gitee用户名')
    parser.add_argument('--gitee-repo', default='', help='Gitee仓库名')
    parser.add_argument('--huawei', default='', help='华为云OBS的version.txt地址')
    parser.add_argument('--version', default=VERSION, help='当前版本')
    
    args = parser.parse_args()
    
    config = {
        'github_owner': args.github_owner,
        'github_repo': args.github_repo,
        'gitee_owner': args.gitee_owner,
        'gitee_repo': args.gitee_repo,
        'huawei_obs_url': args.huawei
    }
    
    result = check_update_multi_source(config, args.version)
    
    print(f"当前版本: {args.version}")
    print(f"最新版本: {result['latest_version']}")
    print(f"有更新: {result['has_update']}")
    print(f"下载链接: {result['download_url']}")
    print(f"来源: {result.get('source', 'unknown')}")
    if result['error']:
        print(f"错误: {result['error']}")
