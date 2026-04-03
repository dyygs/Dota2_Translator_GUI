# -*- coding: utf-8 -*-
"""
Dota 2 中文→英文翻译器 - GUI版本
功能：现代化界面 + 系统托盘 + 自定义触发键
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import keyboard
import pyperclip
import pyautogui
import time
import threading
import requests
import re
import hashlib
import json
import os
from PIL import Image, ImageDraw


class Config:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "trigger_key": "f6",
        "toggle_hotkey": "ctrl+alt+t",
        "cooldown": 0.2,
        "source_lang": "zh-CN",
        "target_lang": "en"
    }
    
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
            except:
                pass
    
    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except:
            pass
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        self.config[key] = value
    
    @property
    def trigger_key(self) -> str:
        return self.get('trigger_key', 'f6')


class TranslationEngine:
    """翻译引擎"""
    
    # Dota2专有词汇对照表
    DOTA2_TERMS = {
        # 物品/装备
        '眼': 'ward',
        '守卫': 'ward',
        '假眼': 'observer ward',
        '真眼': 'sentry ward',
        '粉': 'dust',
        '显尘': 'dust',
        '雾': 'smoke',
        '诡计之雾': 'smoke',
        '大药': 'tango',
        '吃树': 'tango',
        '大魔棒': 'magic stick',
        '魔棒': 'magic stick',
        '吹风': 'wind lace',
        '风衣': 'wind lace',
        '魂戒': 'soul ring',
        '骨灰': 'urn',
        '骨灰盒': 'urn',
        '相位': 'phase boots',
        '假腿': 'power treads',
        '假肢': 'power treads',
        '飞鞋': 'boots of travel',
        '推推': 'force staff',
        '推推棒': 'force staff',
        '微光': 'glimmer cape',
        '微光披风': 'glimmer cape',
        '莲花': 'lotus orb',
        '盘子': 'pavise',
        '大推': 'blink dagger',
        '跳刀': 'blink dagger',
        'BKB': 'black king bar',
        '黑黄': 'black king bar',
        '分身': 'Manta Style',
        '分身斧': 'Manta Style',
        '晕锤': 'skull basher',
        '大锤': 'skull basher',
        '撒旦': 'satanic',
        '大吸': 'satanic',
        '冰眼': 'eye of skadi',
        'mkb': 'monkey king bar',
        '大炮': 'daedalus',
        '金箍棒': 'daedalus',
        '蝴蝶': 'butterfly',
        '圣剑': 'divine rapier',
        '大根': 'dagon',
        '羊刀': 'sheepstick',
        '邪恶镰刀': 'sheepstick',
        '紫苑': 'orchid',
        '血棘': 'bloodthorn',
        '否决': 'nullifier',
        '大隐刀': 'silver edge',
        '隐刀': 'shadow blade',
        '否决挂件': 'nullifier',
        '天堂': 'heaven\'s halberd',
        '雷锤': 'mjollnir',
        '大电': 'mjollnir',
        '强袭': 'assault cuirass',
        '强袭胸甲': 'assault cuirass',
        '龙心': 'heart of tarrasque',
        '龙芯': 'heart of tarrasque',
        '挑战': 'hood of defiance',
        '挑战头巾': 'hood of defiance',
        '刃甲': 'blade mail',
        '反甲': 'blade mail',
        '梅肯': 'mekansm',
        '梅肯笛子': 'mekansm',
        '笛子': 'guardian greaves',
        '绿鞋': 'arcane boots',
        '秘法鞋': 'arcane boots',
        '补刀斧': 'quelling blade',
        '穷鬼盾': 'poor man\'s shield',
        '天鹰': 'ring of aquila',
        '战鼓': 'drum of endurance',
        '勋章': 'medallion of courage',
        '祭品': 'vladmir\'s offering',
        
        # 英雄简称
        '小黑': 'Drow Ranger',
        '小白': 'Crystal Maiden',
        '小黑': 'Drow',
        '火女': 'Lina',
        '冰女': 'Crystal Maiden',
        'pom': 'Phantom Assassin',
        'pa': 'Phantom Assassin',
        '虚空': 'Void',
        'ug': 'Underlord',
        '屠夫': 'Pudge',
        '兽王': 'Beastmaster',
        '小强': 'Nyx Assassin',
        '蚂蚁': 'Weaver',
        '蚂蚁': 'Weaver',
        'wl': 'Witch Doctor',
        'wd': 'Witch Doctor',
        'vs': 'Vengeful Spirit',
        'sv': 'Shadow Shaman',
        'ss': 'Shadow Shaman',
        'coco': 'Crystal Maiden',
        'cm': 'Crystal Maiden',
        'dk': 'Dragon Knight',
        'lr': 'Lina',
        'es': 'Earthshaker',
        'oe': 'Outworld Devourer',
        'od': 'Outworld Devourer',
        'tb': 'Terrorblade',
        'am': 'Anti-Mage',
        'sa': 'Stealth Assassin',
        'naga': 'Naga Siren',
        'ns': 'Night Stalker',
        'sb': 'Spirit Breaker',
        'bb': 'Spirit Breaker',
        'brood': 'Broodmother',
        'bone': 'Clinkz',
        'clinkz': 'Clinkz',
        'riki': 'Riki',
        'bh': 'Bounty Hunter',
        'veno': 'Venomancer',
        'vp': 'Venomancer',
        'dt': 'Dark Seer',
        'ds': 'Dark Seer',
        'puck': 'Puck',
        'pugna': 'Pugna',
        'lok': 'Chen',
        'chen': 'Chen',
        'ench': 'Enchantress',
        'enchant': 'Enchantress',
        'ld': 'Lone Druid',
        'sd': 'Shadow Demon',
        'omniknight': 'Omniknight',
        'omni': 'Omniknight',
        'sven': 'Sven',
        'ck': 'Chaos Knight',
        'und': 'Undying',
        'lycan': 'Lycan',
        'np': 'Nature\'s Prophet',
        'furion': 'Nature\'s Prophet',
        'potm': 'Mirana',
        'mirana': 'Mirana',
        'invoker': 'Invoker',
        'kunkka': 'Kunkka',
        'tk': 'Techies',
        'techies': 'Techies',
        'rubick': 'Rubick',
        'disruptor': 'Disruptor',
        'rubick': 'Rubick',
        
        # 技能/状态
        '推塔': 'push tower',
        '打塔': 'hit tower',
        '拆塔': 'destroy tower',
        '拿塔': 'take tower',
        '高地': 'high ground',
        '下路': 'bottom lane',
        '上路': 'top lane',
        '中路': 'mid lane',
        '野区': 'jungle',
        '远古': 'ancient camp',
        '大野': 'ancient camp',
        '小野': 'small camp',
        '控线': 'lane control',
        '拉野': 'pull',
        '堆野': 'stack',
        '封野': 'block camp',
        'tp': 'town portal',
        '回城': 'town portal',
        '传送': 'town portal',
        '买活': 'buyback',
        '活': 'buyback',
        '死': 'dead',
        '没血': 'low hp',
        '没蓝': 'out of mana',
        '没魔': 'out of mana',
        '闪避': 'evasion',
        '暴击': 'crit',
        '否决': 'nullify',
        '林肯': 'linken sphere',
        '分身': 'illusion',
        '召唤物': 'summons',
        
        # 战术用语
        'gank': 'gank',
        '抓人': 'gank',
        '游走': 'roam',
        '支援': 'rotate',
        '先手': 'initiate',
        '后手': 'follow up',
        '反手': 'counter',
        '打团': 'teamfight',
        '团战': 'teamfight',
        '带线': 'split push',
        '刷钱': 'farm',
        '打钱': 'farm',
        '发育': 'farm',
        '输出': 'damage',
        '肉': 'tank',
        '肉盾': 'tank',
        '核心': 'carry',
        '大哥': 'carry',
        '辅助': 'support',
        '酱油': 'support',
        '劣势路': 'offlane',
        '优势路': 'safe lane',
        '劣势': 'losing',
        '优势': 'winning',
        '等cd': 'wait for cooldown',
        '没大': 'ult on cooldown',
        '大了': 'ult ready',
        
        # 常见交流
        'miss': 'miss',
        '消失': 'missing',
        '不见了': 'missing',
        '小心': 'careful',
        '注意': 'watch out',
        '撤退': 'retreat',
        '跑': 'run',
        '送': 'feed',
        '别送': 'dont feed',
        '别浪': 'dont throw',
        '稳住': 'play safe',
        '上高': 'push high ground',
        '上高地': 'push high ground',
        '拆基地': 'destroy ancient',
        '赢了': 'we win',
        'gg': 'gg',
        'ggwp': 'gg wp',
        'ez': 'ez',
        'nice': 'nice',
        '谢谢': 'thanks',
        'thx': 'thanks',
        'sorry': 'sorry',
        'sorry': 'my bad',
        'ok': 'ok',
        '收到': 'copy',
        '明白': 'got it',
        '一会': 'wait',
        '等我': 'wait for me',
        '我来': 'im coming',
        '看看': 'check',
        '打盾': 'do roshan',
        '杀肉山': 'do roshan',
        '肉山': 'roshan',
        '盾': 'aegis',
        '不朽盾': 'aegis',
        '奶': 'heal',
        '加血': 'heal',
        '救': 'save',
        '保': 'protect',
        '清': 'clear',
        'aoe': 'aoe',
        '点控': 'single target stun',
        '群控': 'aoe stun',
        '减速': 'slow',
        '沉默': 'silence',
        '驱散': 'purge',
        '爆发': 'burst',
        '持续伤害': 'dot',
        'dot': 'damage over time',
    }
    
    def __init__(self):
        self.cache = {}
        self.session = requests.Session()
        
    def replace_chinese_terms(self, text: str) -> str:
        """在翻译前替换中文Dota2词汇"""
        replaced = text
        for cn, en in self.DOTA2_TERMS.items():
            replaced = replaced.replace(cn, en)
        return replaced
    
    def has_only_dota2_terms(self, text: str) -> str:
        """检查文本是否只包含Dota2词汇（不需要通用翻译）"""
        # 检查是否只包含英文Dota2术语和基本词汇
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        if not chinese_pattern.search(text):
            # 没有中文字符，检查是否包含英文Dota2术语
            for en in self.DOTA2_TERMS.values():
                if en.lower() in text.lower():
                    return True
        return False
        
    def optimize_dota2_terms(self, text: str) -> str:
        """优化Dota2专有词汇 - 强制替换所有可能的翻译"""
        optimized = text
        
        # 创建一个从英文翻译回Dota2术语的映射（处理各种可能的翻译变体）
        translation_fixes = {
            # 眼/眼睛/eyes -> ward
            r'\beyes?\b': 'ward',
            r'\beye\b': 'ward',
            
            # 雾/fog -> smoke
            r'\bfog\b': 'smoke',
            
            # 跳刀/blink -> blink dagger
            r'\bblink\b(?! dagger)': 'blink',
            
            # 塔/tower -> tower
            r'\btowers?\b': 'tower',
            
            # 药/tangoes? -> tango
            r'\btangoes?\b': 'tango',
            r'\bhealth?\s?pot(?!ion)': 'tango',
            
            # 矛/spear -> spear (for glaive)
            r'\bspear\b': 'spear',
            
            # 血/mana -> 保留原样
            
            # 杀/kill -> kill
            r'\bkills?\b': 'kill',
        }
        
        for pattern, replacement in translation_fixes.items():
            optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE)
        
        # 强制替换常见的错误翻译
        forced_fixes = {
            'eyes': 'ward',
            'eye': 'ward', 
            'fog': 'smoke',
            'buy a eye': 'buy ward',
            'buy eye': 'buy ward',
            'an eye': 'ward',
        }
        
        for wrong, correct in forced_fixes.items():
            optimized = optimized.replace(wrong, correct)
        
        return optimized
        
    def translate(self, text: str, source_lang='zh-CN', target_lang='en') -> str:
        if not text.strip():
            return text
            
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 先替换中文Dota2词汇
        text_to_translate = self.replace_chinese_terms(text)
            
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {'q': text_to_translate, 'langpair': f'{source_lang}|{target_lang}'}
            resp = self.session.get(url, params=params, timeout=5)
            result = resp.json()
            
            if result.get('responseStatus') == 200:
                translated = result['responseData']['translatedText']
                if translated and translated != text:
                    # 再次优化确保完整
                    translated = self.optimize_dota2_terms(translated)
                    self.cache[cache_key] = translated
                    return translated
        except:
            pass
            
        return text


class Dota2TranslatorGUI:
    """Dota2翻译器GUI主程序"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dota 2 中文翻译器")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 初始化组件
        self.config = Config()
        self.engine = TranslationEngine()
        self.enabled = True
        self.is_translating = False
        self.last_time = 0
        self.is_setting_key = False
        
        # 系统托盘
        self.tray_icon = None
        self.is_minimized = False
        
        # 创建界面
        self._create_widgets()
        
        # 启动键盘监听
        self._start_keyboard_listener()
        
        # 创建系统托盘
        self._create_tray_icon()
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="🎮 Dota 2 中文→英文翻译器",
            font=('Microsoft YaHei UI', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # 状态面板
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="● 已启动")
        self.status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            font=('Microsoft YaHei UI', 11),
            foreground='green'
        )
        self.status_label.pack(anchor='w')
        
        self.trigger_key_var = tk.StringVar(value=f"触发键: {self.config.trigger_key.upper()}")
        ttk.Label(status_frame, textvariable=self.trigger_key_var).pack(anchor='w')
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        # 按钮行1
        btn_frame1 = ttk.Frame(control_frame)
        btn_frame1.pack(fill=tk.X, pady=5)
        
        self.toggle_btn = ttk.Button(
            btn_frame1, 
            text="禁用翻译", 
            command=self.toggle_translation,
            width=15
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        
        self.set_key_btn = ttk.Button(
            btn_frame1, 
            text="设置触发键", 
            command=self.start_set_key,
            width=15
        )
        self.set_key_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame1, 
            text="测试翻译", 
            command=self.test_translation,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # 按钮行2
        btn_frame2 = ttk.Frame(control_frame)
        btn_frame2.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            btn_frame2, 
            text="最小化到托盘", 
            command=self.minimize_to_tray,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame2, 
            text="保存配置", 
            command=self.save_config,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # 设置提示
        self.key_hint_label = ttk.Label(
            control_frame,
            text="",
            font=('Microsoft YaHei UI', 9),
            foreground='blue'
        )
        self.key_hint_label.pack(anchor='w', pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=12,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部状态栏
        self.bottom_status = tk.StringVar(value="就绪 | 按 Ctrl+Alt+T 切换开关")
        ttk.Label(
            main_frame, 
            textvariable=self.bottom_status,
            relief=tk.SUNKEN
        ).pack(fill=tk.X, pady=(5, 0))
        
        # 初始日志
        self.log("系统启动成功")
        self.log(f"触发键: {self.config.trigger_key.upper()}")
        self.log("等待Dota2聊天框输入...")
        
    def log(self, message: str):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.bottom_status.set(message)
        
    def toggle_translation(self):
        """切换翻译开关"""
        self.enabled = not self.enabled
        if self.enabled:
            self.status_var.set("● 已启动")
            self.status_label.config(foreground='green')
            self.toggle_btn.config(text="禁用翻译")
            self.log("翻译功能已启用")
        else:
            self.status_var.set("● 已禁用")
            self.status_label.config(foreground='red')
            self.toggle_btn.config(text="启用翻译")
            self.log("翻译功能已禁用")
            
    def start_set_key(self):
        """开始设置触发键"""
        self.is_setting_key = True
        self.set_key_btn.config(state='disabled')
        self.key_hint_label.config(text="请按下您想使用的触发键（如 F7、空格等）...")
        self.log("等待按键输入...")
        
    def on_key_pressed(self, event):
        """按键事件处理"""
        if self.is_setting_key:
            # 设置触发键模式
            key_name = event.name.lower()
            valid_keys = [
                'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
                'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                'space', 'enter', 'tab'
            ]
            
            if key_name in valid_keys:
                self.config.set('trigger_key', key_name)
                key_display = key_name.upper() if len(key_name) == 1 else key_name
                self.trigger_key_var.set(f"触发键: {key_display}")
                self.key_hint_label.config(text=f"✓ 触发键已设置为: {key_display}")
                self.log(f"触发键已设置为: {key_display}")
                self.is_setting_key = False
                self.set_key_btn.config(state='normal')
            return
        
        # 正常翻译模式
        if event.name.lower() == self.config.trigger_key.lower():
            if self.enabled and not self.is_translating:
                current_time = time.time()
                cooldown = self.config.get('cooldown', 0.2)
                if current_time - self.last_time > cooldown:
                    self.last_time = current_time
                    threading.Thread(target=self.do_translate, daemon=True).start()
    
    def do_translate(self):
        """执行翻译"""
        try:
            self.is_translating = True
            
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.03)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.03)
            
            text = pyperclip.paste()
            
            if text and re.search(r'[\u4e00-\u9fff]', text):
                self.log(f"检测到中文: {text[:30]}...")
                
                translated = self.engine.translate(text)
                
                if translated and translated != text:
                    pyperclip.copy(translated)
                    time.sleep(0.02)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.02)
                    pyautogui.press('enter')
                    
                    self.log(f"翻译: {translated[:30]}...")
                    
        except Exception as e:
            self.log(f"错误: {e}")
        finally:
            self.is_translating = False
            
    def test_translation(self):
        """测试翻译功能"""
        test_text = "你好世界"
        self.log(f"测试翻译: {test_text}")
        result = self.engine.translate(test_text)
        self.log(f"结果: {result}")
        messagebox.showinfo("测试结果", f"原文: {test_text}\n译文: {result}")
        
    def save_config(self):
        """保存配置"""
        self.config.save_config()
        self.log("配置已保存")
        messagebox.showinfo("保存成功", "配置已保存到 config.json")
        
    def _start_keyboard_listener(self):
        """启动键盘监听"""
        keyboard.hook(self.on_key_pressed)
        keyboard.add_hotkey('ctrl+alt+t', self.toggle_translation)
        
    def _create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            import pystray
            
            # 创建图标图像
            def create_icon_image():
                image = Image.new('RGB', (64, 64), color=(70, 130, 180))
                dc = ImageDraw.Draw(image)
                dc.rectangle([16, 16, 48, 48], fill='white')
                return image
            
            # 托盘菜单
            def on_show(icon, item):
                self.root.after(0, self.restore_from_tray)
                
            def on_exit(icon, item):
                self.root.after(0, self.quit_app)
                
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", on_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", on_exit)
            )
            
            self.tray_icon = pystray.Icon(
                "dota2_translator",
                create_icon_image(),
                "Dota 2 翻译器",
                menu
            )
            
            # 在后台线程运行托盘
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            self.log(f"托盘初始化失败: {e}")
            
    def minimize_to_tray(self):
        """最小化到系统托盘"""
        self.root.withdraw()
        self.is_minimized = True
        if self.tray_icon:
            self.tray_icon.visible = True
            
    def restore_from_tray(self):
        """从托盘恢复窗口"""
        self.root.deiconify()
        self.is_minimized = False
        if self.tray_icon:
            self.tray_icon.visible = False
            
    def _on_closing(self):
        """窗口关闭事件"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit_app()
        
    def quit_app(self):
        """退出程序"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """运行GUI"""
        self.root.mainloop()


if __name__ == "__main__":
    app = Dota2TranslatorGUI()
    app.run()
