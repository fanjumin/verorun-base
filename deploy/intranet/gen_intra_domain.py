#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_intra_domain.py — VeroRun 企业内网域名生成/校验工具

功能：
  1. 校验用户自建的内网后缀/域名，排除：
     - 真实公网 TLD（IANA 列表，联网刷新 + 内置兜底）
     - 保留域（RFC 2606/6761/6762/7686：test/invalid/localhost/example/local/onion/alt）
     - 非法格式（字符集 / 连字符 / 连续点 / 后缀长度 < 2）
  2. 通过后输出可直接用于官方部署的值（DEPLOY_DOMAIN / DEPLOY_PROTOCOL）

用法：
  python3 gen_intra_domain.py office            # 自建后缀（自动补全为 verorun.office）
  python3 gen_intra_domain.py mycorp.office     # 自建完整域名
  python3 gen_intra_domain.py --prefix ***REMOVED*** office
  python3 gen_intra_domain.py --random          # 自动生成一个可用建议
  python3 gen_intra_domain.py --check-dns verorun.office   # 附加公网 DNS 探测（仅警告）
  python3 gen_intra_domain.py --list-forbidden  # 查看排除名单

特性：幂等、无副作用（仅 /tmp 下 TLD 缓存）、联网调用带超时、失败即回退。
"""
import argparse
import os
import random
import re
import socket
import sys
import time
import urllib.request

PREFIX_DEFAULT = "verorun"
IANA_URL = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
CACHE_PATH = "/tmp/verorun_tlds_cache.txt"
CACHE_MAX_AGE = 7 * 24 * 3600  # 缓存 7 天
FETCH_TIMEOUT = 10             # 有界：单次超时，失败即回退，不重试循环

# ── 保留域：任何情况下禁止使用 ──
RESERVED_TLDS = {
    "test", "invalid", "localhost", "example", "local", "onion", "alt",
}

# ── 内置兜底 TLD 列表（联网拉取 IANA 失败时使用；联网成功以 IANA 为准）──
FALLBACK_TLDS = {
    "com", "net", "org", "cn", "top", "xyz", "vip", "club", "shop", "store",
    "online", "site", "tech", "fun", "app", "dev", "io", "ai", "co", "me",
    "info", "biz", "cc", "tv", "name", "mobi", "asia", "red", "win", "link",
    "live", "plus", "group", "team", "city", "world", "company", "email",
    "media", "news", "blog", "wiki", "space", "cloud", "host", "digital",
    "network", "solutions", "systems", "services", "agency", "center",
    "pro", "work", "zone", "best", "cool", "directory", "discount", "download",
    "express", "expert", "faith", "family", "fashion", "film", "finance",
    "financial", "fish", "fit", "fitness", "flowers", "football", "forsale",
    "forum", "foundation", "fund", "furniture", "futbol", "fyi", "gallery",
    "game", "games", "garden", "gift", "gifts", "glass", "global", "gmbh",
    "gold", "golf", "graphics", "green", "gripe", "guru", "haus", "health",
    "healthcare", "help", "here", "hiphop", "hockey", "holdings", "holiday",
    "horse", "hospital", "hosting", "hot", "house", "how", "immo", "immobilien",
    "industries", "ing", "ink", "institute", "insure", "international",
    "investments", "irish", "jetzt", "jewelry", "juegos", "kaufen", "kim",
    "kitchen", "kiwi", "land", "lease", "legal", "lgbt", "life", "lighting",
    "limited", "limo", "loan", "loans", "lotto", "love", "ltda", "luxe",
    "luxury", "makeup", "management", "market", "marketing", "markets", "mba",
    "melbourne", "memorial", "men", "menu", "miami", "moe", "mom", "money",
    "monster", "movie", "museum", "navy", "ngo", "ninja", "onl", "ooo",
    "organic", "partners", "parts", "party", "pet", "pharmacy", "photo",
    "photography", "photos", "physio", "pics", "pictures", "pink", "pizza",
    "place", "play", "plumbing", "poker", "press", "productions", "prof",
    "promo", "properties", "property", "protection", "pub", "pwc", "qpon",
    "quest", "racing", "radio", "realtor", "realty", "recipes", "rehab",
    "reise", "reisen", "rent", "rentals", "repair", "report", "republican",
    "rest", "restaurant", "review", "reviews", "rich", "rip", "rocks", "rodeo",
    "run", "ryukyu", "saarland", "sale", "sarl", "school", "schule", "science",
    "scot", "security", "sex", "sexy", "shiksha", "shoes", "show", "singles",
    "ski", "soccer", "social", "software", "solar", "sony", "sport", "spot",
    "star", "storage", "stream", "studio", "study", "style", "sucks", "supplies",
    "supply", "support", "surf", "surgery", "tattoo", "tax", "taxi", "technology",
    "tennis", "theater", "theatre", "tienda", "tips", "tires", "tirol", "today",
    "tools", "tours", "town", "toys", "trade", "trading", "training", "tube",
    "university", "uno", "vacations", "ventures", "vet", "viajes", "video",
    "villas", "vin", "vision", "vodka", "vote", "voting", "voto", "voyage",
    "wang", "watch", "webcam", "website", "wed", "wedding", "wiki", "wine",
    "works", "wtf", "xin", "yoga", "you", "za", "zip", "zone", "arpa",
    # 中文 IDN TLD（punycode 形式，与 IANA 一致）
    "xn--fiqs8s",   # 中国
    "xn--55qx5d",   # 公司
    "xn--io0a7i",   # 网络
    "xn--czr694b",  # 企业
    "xn--vuq861b",  # 信息
    "xn--ses554g",  # 网址
    "xn--hxt814e",  # 网站
    "xn--3pxu8k",   # 电话
    "xn--rhqv96g",  # 购物
    "xn--kput3i",   # 手机
}

SUGGESTION_WORDS = [
    "hub", "gate", "core", "zone", "nest", "base", "portal", "oasis", "forge",
    "nexus", "prime", "ridge", "beacon", "harbor", "atlas", "delta", "alpha",
    "omega", "nova", "pulse", "orbit", "apex", "summit", "stream", "grove",
    "meadow", "watch", "guard", "vault", "bench", "dock",
]

LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def log(msg):
    sys.stdout.write(msg + "\n")


def fail(msg, code=1):
    sys.stderr.write("FAIL: " + msg + "\n")
    sys.exit(code)


def load_real_tlds():
    """优先 IANA 联网列表（带 /tmp 缓存），失败回退内置列表。返回小写集合。"""
    # 1) 读缓存（存在且未过期）
    if os.path.isfile(CACHE_PATH):
        try:
            age = time.time() - os.path.getmtime(CACHE_PATH)
            if age <= CACHE_MAX_AGE:
                with open(CACHE_PATH, "r", encoding="utf-8") as fh:
                    tlds = {line.strip().lower() for line in fh if line.strip()}
                if tlds:
                    return tlds
        except (OSError, IOError):
            pass
    # 2) 联网拉取 IANA 列表（有界超时，失败即回退，无重试循环）
    try:
        req = urllib.request.Request(IANA_URL, headers={"User-Agent": "verorun-gen-intra-domain"})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            data = resp.read().decode("utf-8", errors="ignore")
        tlds = {
            line.strip().lower()
            for line in data.splitlines()
            if line.strip() and not line.startswith("#")
        }
        if tlds:
            try:
                with open(CACHE_PATH, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(sorted(tlds)) + "\n")
            except (OSError, IOError):
                pass
            return tlds
    except Exception:
        pass
    return FALLBACK_TLDS


def normalize(raw):
    """去空白、转小写、剥首尾点。"""
    s = raw.strip().lower()
    return s.strip(".")


def validate_labels(name):
    """校验整名（至少两段、每段合法、总长不超限）。"""
    if "." not in name:
        return False, "必须包含点（至少两段），单标签无法承载跨子域 SSO cookie。"
    if len(name) > 253:
        return False, "域名总长度超过 253 字符。"
    labels = name.split(".")
    if any(not LABEL_RE.match(lb) for lb in labels):
        return False, "存在非法标签：仅允许 a-z / 0-9 / 内部连字符，不以连字符开头或结尾，单段最长 63 字符。"
    if len(labels[-1]) < 2:
        return False, "后缀（最后一段）长度必须 ≥ 2 个字母。"
    return True, ""


def check_tld(tld, real_tlds):
    if tld in RESERVED_TLDS:
        return False, "保留域不可用：.{0}（RFC 保留，行为已被标准定义死）。".format(tld)
    if tld in real_tlds:
        return False, "该后缀是公网真实 TLD：.{0}——DNS 泄漏会解析到公网，禁止使用。".format(tld)
    return True, ""


def dns_probe(fqdn, timeout=3):
    """公网探测：若该名能被公网解析到非本机地址，返回警告文案；异常视为不可解析。"""
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            ips = set()
            for info in socket.getaddrinfo(fqdn, None, socket.AF_INET):
                ips.add(info[4][0])
        finally:
            socket.setdefaulttimeout(old_timeout)
        if not ips or ips == {"127.0.0.1"}:
            return None
        return "警告：{0} 在公网可解析到 {1}，请确认内网 DNS/hosts 覆盖优先。".format(
            fqdn, ", ".join(sorted(ips)))
    except Exception:
        return None


def print_result(fqdn, notes):
    log("")
    log("OK: 内网域名可用 -> {0}".format(fqdn))
    log("可写入 .env 的配置：")
    log("  DEPLOY_DOMAIN={0}".format(fqdn))
    log("  DEPLOY_PROTOCOL=https")
    for note in notes:
        log("  提示: " + note)
    log("")


def main():
    parser = argparse.ArgumentParser(
        description="VeroRun 企业内网域名生成/校验工具（排除真实 TLD 与保留域，允许用户自建）")
    parser.add_argument("name", nargs="?",
                        help="内网后缀（如 office）或完整域名（如 mycorp.office）")
    parser.add_argument("--prefix", default=PREFIX_DEFAULT,
                        help="单标签后缀自动补全的前缀，默认 {0}".format(PREFIX_DEFAULT))
    parser.add_argument("--random", action="store_true", help="自动生成一个可用后缀建议")
    parser.add_argument("--check-dns", action="store_true", help="附加公网 DNS 探测（仅警告）")
    parser.add_argument("--list-forbidden", action="store_true", help="查看排除名单")
    args = parser.parse_args()

    if args.list_forbidden:
        real = load_real_tlds()
        log("真实公网 TLD 数量（IANA/内置兜底）：{0}".format(len(real)))
        log("保留域：{0}".format(", ".join(sorted(RESERVED_TLDS))))
        log("完整真实 TLD 名单：https://data.iana.org/TLD/tlds-alpha-by-domain.txt")
        return 0

    if not args.name and not args.random:
        parser.print_help()
        return 1

    real_tlds = load_real_tlds()
    notes = []

    if args.random:
        chosen = None
        for _ in range(50):
            cand = random.choice(SUGGESTION_WORDS)
            if cand in RESERVED_TLDS or cand in real_tlds:
                continue
            chosen = cand
            break
        if chosen is None:
            fail("随机生成失败（词库均被排除），请手动指定后缀。")
        tld = chosen
        name = args.prefix + "." + chosen
        log("自动建议后缀：{0}".format(tld))
    else:
        name = normalize(args.name)
        if not name:
            fail("输入为空。")
        if "." not in name:
            # 用户只给了单标签后缀 → 自动补全前缀
            name = args.prefix + "." + name
            notes.append("已自动补全为 {0}.<后缀>（可用 --prefix 修改）。".format(args.prefix))
        tld = name.split(".")[-1]

    ok, msg = validate_labels(name)
    if not ok:
        fail(msg)
    ok, msg = check_tld(tld, real_tlds)
    if not ok:
        fail(msg)

    if args.check_dns:
        w = dns_probe(name)
        if w:
            notes.append(w)

    print_result(name, notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
