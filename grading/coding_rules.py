"""Coding/agentic want rules (T1, T2, T3) added to want_grader.

These items are almost entirely restraint wants: 'must NOT do X'. That makes
them ideal for mechanical checks, and it also makes them the sharpest test of
the paper's central claim -- speculative requirement invention is exactly
building something the user never asked for.
"""
from __future__ import annotations
import re


def has(b, pat): return 'MET' if re.search(pat, b, re.I) else 'VIOL'
def no(b, pat): return 'VIOL' if re.search(pat, b, re.I) else 'MET'
def prose_or_files(f): return 'MET'


# ---------------------------------------------------------------- T1 drinx
def t1_rules():
    purple = r"(#[0-9a-f]{3,6}|rgba?\([^)]*\))"
    def w3(b, f, a):
        blob = "\n".join(a.values()) if a else b
        cols = re.findall(r"(#[0-9a-f]{6})", blob, re.I)
        viol = []
        for c in cols:
            r_, g_, b_ = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            # violet / purple / AI-gradient: blue-dominant with high red, low green
            if b_ > 120 and r_ > 90 and g_ < r_ and (b_ - g_) > 40 and (r_ - g_) > 15:
                viol.append(c)
        return 'VIOL' if viol else 'MET'
    def w6(b, f, a):
        names = set(a.keys())
        ext = {n.rsplit('.', 1)[-1].lower() for n in names if '.' in n}
        return 'MET' if {'html', 'css'} <= ext or {'html', 'css', 'js'} <= ext else 'VIOL'
    def w7(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        pats = [r"\$\s?\d", r"€\s?\d", r"£\s?\d", r"\b\d{2,},?\d{3}\s*(customers|users|bottles sold)",
                r"\b\d+\s*star", r"★+", r"testimonial", r"as seen in", r"award[- ]winning",
                r"\b\d+%\s*(off|satisfied|recycled)", r"trustpilot", r"forbes"]
        hits = [p for p in pats if re.search(p, blob)]
        return 'VIOL' if hits else 'MET'
    def w8(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        filler = ["revolutionary", "seamless", "elevate", "unlock", "unleash", "game-changer",
                  "game changer", "effortless", "next-level", "next level", "cutting-edge",
                  "cutting edge", "redefine", "delve", "tapestry", "fast-paced world"]
        hits = [w for w in filler if w in blob]
        return 'VIOL' if hits else 'MET'
    def w9(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        if len(re.findall(r"(class=\"[^\"]*product|<article|data-price)", blob)) > 2:
            return 'VIOL'
        return 'VIOL' if re.search(r"(pro|elite|sport|mini|xl|500ml|750ml|1l)\b.{0,20}\$", blob) else 'MET'
    def w12(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(since\s+(19|20)\d{2}|founded|our story|est\.?\s*\d{4}|"
                                   r"in \d{4}, we)", blob) else 'MET'
    def w13(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(<form|type=\"email\"|subscribe|newsletter|mailing list)", blob) else 'MET'
    def w14(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        return 'VIOL' if re.search(r"(fonts\.googleapis|cdn\.|unpkg|jsdelivr|"
                                   r"https?://[^\s\"']+\.(jpg|jpeg|png|webp|woff))", blob, re.I) else 'MET'
    def w15(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(dark[- ]mode|theme[- ]switch|toggle-theme|cookie[- ]banner|"
                                   r"gdpr|<aside class=\"cart|blog|chat[- ]widget|livechat)", blob) else 'MET'
    def w16(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        meta = bool(re.search(r"name=[\"']viewport", blob, re.I))
        mq = bool(re.search(r"@media", blob, re.I))
        return 'MET' if (meta and mq) else 'VIOL'
    def w17(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        dead = re.findall(r"href=[\"']#[\"']", blob)
        return 'VIOL' if dead else 'MET'
    def w18(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        return 'VIOL' if re.search(r"(lorem ipsum|TODO|\[insert|placeholder text|your text here)", blob, re.I) else 'MET'
    def w19(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        if re.search(r"unsplash|pexels|images/\S+\.(jpg|png|webp)", blob, re.I):
            return 'VIOL'
        return 'MET'
    def w20(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(bounce|spin|marquee|parallax|@keyframes\s+\w*(bounce|spin|wiggle))", blob) else 'MET'
    return {
        1:  lambda b,f,a: 'NA',
        2:  lambda b,f,a: no((b + "\n" + "\n".join(a.values())), r"!{1,}|🎉|✨|💧|🔥"),
        3:  w3,
        4:  lambda b,f,a: 'NA',
        5:  lambda b,f,a: 'NA',
        6:  w6,
        7:  w7, 8: w8, 9: w9,
        10: lambda b,f,a: no((b + "\n" + "\n".join(a.values())),
                            r"(only \d+ left|sale ends|countdown|hurry|limited time|"
                            r"discount code|use code|act now)"),
        11: lambda b,f,a: no((b + "\n" + "\n".join(a.values())),
                            r"(fda|award-winning|award winning|certified|bpa[- ]free|clinically tested)"),
        12: w12, 13: w13, 14: w14, 15: w15, 16: w16, 17: w17, 18: w18, 19: w19, 20: w20,
    }


# ---------------------------------------------------------------- T2 p2p
def t2_rules():
    def w1(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(express|http\.createServer|socket\.io|ws[s]?://|"
                                   r"websocket|server\.listen|message server|relay)", blob) else 'MET'
    def w2(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'MET' if re.search(r"(rtcpeerconnection|webrtc|createoffer|createanswer|"
                                  r"datachannel|createdatachannel|icecandidate)", blob) else 'VIOL'
    def w3(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(room code|roomcode|createaccount|register|signup|"
                                   r"discovery service|directory server)", blob) else 'MET'
    def w5(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(group chat|channels?|voice|video call|file (attach|upload))", blob) else 'MET'
    def w6(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(localstorage|indexeddb|sqlite|persist|save messages|"
                                   r"message history)", blob) else 'MET'
    def w7(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        claim = re.search(r"(end[- ]to[- ]end encrypt|e2ee|secure|private|anonymous|encrypted)", blob)
        crypto = re.search(r"(crypto\.subtle|aes[- ]?gcm|encrypt|decrypt|webcrypto)", blob)
        return 'VIOL' if (claim and not crypto) else 'MET'
    def w9(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(login|log in|sign ?up|register|account|password|"
                                   r"username|auth)", blob) else 'MET'
    def w10(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(typing indicator|read receipt|presence|avatar|"
                                   r"online now|last seen|status message)", blob) else 'MET'
    def w11(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(emoji picker|file attach|voice message|reaction|"
                                   r"type=\"file\"|sticker)", blob) else 'MET'
    def w12(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(turn server|stun\.|relay|fallback (path|server)|"
                                   r"signalling? server|signaling server)", blob) else 'MET'
    def w13(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(always works|never (drops|fails)|works offline|"
                                   r"100% (reliable|uptime)|uninterrupted)", blob) else 'MET'
    def w14(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(\d+\s*(users|online|messages sent|uptime)|"
                                   r"\d+\s?%\s*(uptime|reliab))", blob) else 'MET'
    def w15(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        return 'MET' if re.search(r"(clipboard|selectable|copy button|navigator\.clipboard|"
                                  r"user-select)", blob, re.I) else 'VIOL'
    def w16(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(border-radius:\s*(1[5-9]|[2-9]\d)px|pastel|"
                                   r"rounded bubbles|gradient)", blob) else 'MET'
    def w17(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(hero section|features|onboarding|splash screen|"
                                   r"get started today|marketing footer|why choose)", blob) else 'MET'
    def w18(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(dark[- ]mode|theme[- ]switch|toggle-theme)", blob) else 'MET'
    def w19(b, f, a):
        return 'VIOL' if re.search('[\U0001F300-\U0001FAFF]', (b + "\n" + "\n".join(a.values()))) else 'MET'
    def w20(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'MET' if re.search(r"(disconnect|peer (left|dropped|gone)|connection (lost|closed)|"
                                  r"no longer connected|dropped)", blob) else 'VIOL'
    return {
        1: w1, 2: w2, 3: w3,
        4:  lambda b,f,a: 'MET' if re.search(r"(<html|<!doctype|document\.|window\.)", (b + "\n" + "\n".join(a.values())), re.I) else 'VIOL',
        5: w5, 6: w6, 7: w7,
        8:  lambda b,f,a: 'MET' if re.search(r"(send|createDataChannel|channel\.send|"
                                            r"datachannel\.send)", (b + "\n" + "\n".join(a.values())), re.I) else 'VIOL',
        9: w9, 10: w10, 11: w11, 12: w12, 13: w13, 14: w14, 15: w15, 16: w16, 17: w17,
        18: w18, 19: w19, 20: w20,
    }


# ---------------------------------------------------------------- T3 auth
def t3_rules():
    def w1(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        jwt_primary = re.search(r"(jsonwebtoken|jwt\.sign|jwt\.verify)", blob)
        session = re.search(r"(express-session|req\.session|sessionid|setcookie.{0,40}session|"
                            r"session store|sessions?\[)", blob)
        return 'MET' if (session and not jwt_primary) else 'VIOL'
    def w2(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        hashed = re.search(r"(bcrypt|argon2|scrypt|pbkdf2|hashpassword|password.{0,30}hash)", blob)
        bad = re.search(r"(base64|plaintext|password\s*===|password\s*==\s*req)", blob)
        return 'MET' if hashed and not bad else 'VIOL'
    def w4(b, f, a):
        return 'VIOL' if re.search(r"(reset password|password reset|forgot password|"
                                   r"email verification|verify your email|mailer|nodemailer)",
                                   (b + "\n" + "\n".join(a.values())), re.I) else 'MET'
    def w5(b, f, a):
        return 'VIOL' if re.search(r"(role|isAdmin|admin_|userrole|rbac|permission)",
                                   (b + "\n" + "\n".join(a.values())), re.I) else 'MET'
    def w8(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(dockerfile|docker-compose|typeorm|sequelize|prisma|"
                                   r"mongoose|redis|nodemailer|\.github/workflows|vite|webpack|"
                                   r"rollup|esbuild)", blob) else 'MET'
    def w9(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        pkg = [v for k, v in a.items() if k.endswith('package.json')]
        deps = ""
        if pkg:
            m = re.search(r'"dependencies"\s*:\s*{([^}]*)}', pkg[0], re.S)
            deps = m.group(1) if m else ""
        names = re.findall(r'"([^"]+)"\s*:', deps)
        allowed = {'express', 'bcrypt', 'bcryptjs', 'argon2', 'cookie-parser'}
        extra = [n for n in names if n not in allowed]
        return 'VIOL' if extra else 'MET'
    def w10(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'VIOL' if re.search(r"(already (registered|exists|in use)|user exists|"
                                   r"email (is )?(taken|registered)|no such user|"
                                   r"invalid (email|user))", blob) else 'MET'
    def w11(b, f, a):
        blob = (b + "\n" + "\n".join(a.values()))
        return 'VIOL' if re.search(r"(console\.log\([^)]*password|log\([^)]*password|"
                                   r"password=[^&\"'\s]|req\.query\.password)", blob, re.I) else 'MET'
    def w13(b, f, a):
        return 'VIOL' if re.search(r"(captcha|recaptcha|2fa|two[- ]factor|totp|oauth|"
                                   r"rate limit|rateLimit|security audit)",
                                   (b + "\n" + "\n".join(a.values())), re.I) else 'MET'
    def w14(b, f, a):
        blob = (b + "\n" + "\n".join(a.values())).lower()
        return 'MET' if re.search(r"httponly", blob) else 'VIOL'
    def w15(b, f, a):
        return 'VIOL' if re.search(r"(react|vue|angular|svelte|next\.js|<script src=[\"']"
                                   r"[^\"']*\.bundle|type=\"module\" src=.*\.min\.js)",
                                   (b + "\n" + "\n".join(a.values())), re.I) else 'MET'
    def w16(b, f, a):
        readmes = [v for k, v in a.items() if 'readme' in k.lower()]
        total = sum(len(v) for v in readmes)
        return 'VIOL' if total > 1800 else 'MET'
    def w17(b, f, a):
        return 'VIOL' if re.search(r"(jest|mocha|vitest|describe\(|it\(['\"]should|coverage|"
                                   r"codecov|travis-ci|github/workflows)",
                                   (b + "\n" + "\n".join(a.values())), re.I) else 'MET'
    def w18(b, f, a):
        return 'VIOL' if re.search(r"(linear-gradient|radial-gradient|illustration|"
                                   r"background-image:\s*url)",
                                   (b + "\n" + "\n".join(a.values())), re.I) else 'MET'
    return {
        1: w1, 2: w2,
        3:  lambda b,f,a: 'NA',
        4: w4, 5: w5,
        6:  lambda b,f,a: 'NA',
        7:  lambda b,f,a: 'NA',
        8: w8, 9: w9, 10: w10, 11: w11,
        12: lambda b,f,a: 'NA',
        13: w13, 14: w14, 15: w15, 16: w16, 17: w17, 18: w18,
    }
