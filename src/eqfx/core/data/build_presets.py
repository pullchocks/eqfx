from __future__ import annotations

# Band map: 0 HP, 1 LS, 2~160, 3~350, 4~700, 5~1.5k, 6~3k, 7~5.5k, 8 HS, 9 LP

PRESETS = []


def P(pid, name, category, description, patches, output_gain=0.0):
    PRESETS.append(
        {
            "id": pid,
            "name": name,
            "category": category,
            "description": description,
            "patches": {str(k): v for k, v in patches.items()},
            "output_gain": output_gain,
        }
    )


def hp(f, q=0.75):
    return {"frequency": f, "q": q, "enabled": True}


def ls(f, g, q=0.8):
    return {"frequency": f, "gain": g, "q": q}


def pk(f, g, q=1.1):
    return {"frequency": f, "gain": g, "q": q}


def hs(f, g, q=0.75):
    return {"frequency": f, "gain": g, "q": q}


def lp(f, q=0.71):
    return {"frequency": f, "q": q, "enabled": True}


# --- Music ---
P("flat", "Flat Reference", "Music", "Unity. Use this to A/B or as a clean starting point.", {})
P("harman-ish", "Harman Target", "Music", "Consumer headphone target: bass shelf and gentle air.", {
    1: ls(60, 4.2, 0.7), 2: pk(150, 1.2, 0.9), 8: hs(10000, 2.4, 0.7),
}, -1.4)
P("bass-boost", "Bass Boost", "Music", "Broad low shelf with a slight mid dip so it stays clean.", {
    1: ls(80, 6.0, 0.7), 4: pk(500, -1.2, 0.9),
}, -1.6)
P("treble-sparkle", "Treble Sparkle", "Music", "Open high shelf from 5 kHz for cymbals and air.", {
    8: hs(5000, 3.8, 0.7),
}, -0.8)
P("warm-analog", "Warm Analog", "Music", "Weight at 200 Hz, softer top like tape/console.", {
    1: ls(90, 1.8, 0.8), 2: pk(200, 2.0, 0.9), 8: hs(10000, -1.8, 0.7),
})
P("club-system", "Club System", "Music", "Huge 50 Hz, scooped mids, bright hats.", {
    1: ls(50, 5.5, 0.9), 4: pk(600, -3.0, 1.0), 8: hs(9000, 2.5, 0.8),
}, -1.5)
P("loudness-night", "Night Loudness", "Music", "Fletcher-Munson lift so quiet playback still has bass and air.", {
    1: ls(80, 3.4, 0.75), 5: pk(1400, -1.2, 0.9), 8: hs(9000, 2.2, 0.8),
}, -1.0)
P("streaming-curve", "Streaming Curve", "Music", "Translation-friendly U with a safe rumble cut.", {
    0: hp(28), 1: ls(70, 0.8, 0.8), 4: pk(600, -0.6, 1.0), 8: hs(12000, 1.1, 0.75),
})
P("hip-hop", "Hip-Hop / 808", "Music", "Sub-heavy with a 1 kHz knock and crisp hats.", {
    1: ls(45, 4.2, 0.9), 2: pk(90, 1.6, 1.3), 5: pk(1100, 2.2, 1.4), 8: hs(10000, 1.8, 0.8),
}, -1.2)
P("edm", "EDM / Electronic", "Music", "Sub, 4 kHz aggression, air for risers.", {
    1: ls(50, 3.6, 0.9), 3: pk(280, -2.0, 1.2), 7: pk(4000, 2.8, 1.1), 8: hs(13000, 2.2, 0.7),
}, -1.0)
P("rock", "Rock Mix", "Music", "Tight bottom, 2.5 kHz attitude, cymbal air.", {
    0: hp(40), 3: pk(300, -1.6, 1.1), 6: pk(2500, 2.2, 1.1), 8: hs(11000, 1.8, 0.75),
}, -0.4)
P("pop-radio", "Pop Radio", "Music", "Smile curve plus vocal presence.", {
    1: ls(90, 1.8, 0.8), 3: pk(300, -1.2, 1.1), 6: pk(2800, 2.0, 1.15), 8: hs(11000, 2.2, 0.75),
}, -0.6)
P("jazz", "Jazz Club", "Music", "Warm room: 150 Hz body, polite presence, no hype.", {
    1: ls(80, 1.2, 0.8), 2: pk(160, 1.4, 1.0), 7: pk(5000, 0.8, 1.0), 8: hs(12000, -0.8, 0.8),
})
P("classical", "Classical Hall", "Music", "Rumble cut, natural 2 kHz sheen, open air.", {
    0: hp(32), 6: pk(2500, 1.0, 1.2), 8: hs(14000, 1.6, 0.7),
})
P("rnb", "R&B Smooth", "Music", "Warm 100 Hz, silky 8 kHz, polite mids.", {
    1: ls(100, 2.2, 0.8), 5: pk(1500, -1.0, 1.0), 8: hs(8000, 2.4, 0.75),
})
P("lofi", "Lo-fi", "Music", "Vinyl bandwidth, warm mids, no sparkle.", {
    0: hp(60), 2: pk(180, 2.0, 1.0), 9: lp(7500, 0.75),
})
P("headphones", "Headphones", "Music", "Slight bass and 8–12 kHz silk for typical cans.", {
    1: ls(70, 2.4, 0.75), 7: pk(5500, -0.8, 1.2), 8: hs(11000, 1.8, 0.7),
}, -0.6)
P("car", "Car Audio", "Music", "Road-noise loudness: bass + presence.", {
    1: ls(70, 4.0, 0.8), 6: pk(2500, 2.0, 1.1), 8: hs(10000, 1.5, 0.8),
}, -1.2)
P("smiley", "Smiley", "Music", "Classic U — bass, scooped mids, air.", {
    1: ls(80, 4.5, 0.75), 4: pk(700, -2.5, 0.9), 8: hs(10000, 4.0, 0.7),
}, -1.5)
P("de-harsh-music", "De-Harsh", "Music", "Tame 2.5–6 kHz grit on bright masters.", {
    6: pk(2800, -2.2, 1.8), 7: pk(5500, -3.0, 1.6),
}, 0.5)

# --- Communication ---
P("team-voice", "Team Voice", "Communication", "HPF, de-boom, 2.7 kHz diction. Built for in-game and Discord.", {
    0: hp(90, 0.8), 2: pk(160, -1.6, 1.2), 3: pk(320, -2.8, 1.3), 6: pk(2700, 3.2, 1.1), 8: hs(9000, 1.0, 0.8),
}, -0.3)
P("discord", "Discord / Overlay", "Communication", "Leave a wide 2–4 kHz lane so overlay chat cuts through the mix.", {
    0: hp(100), 3: pk(350, -2.4, 1.2), 5: pk(1600, -1.0, 1.0), 6: pk(2500, 3.4, 1.05), 7: pk(4000, 2.0, 1.2),
}, -0.4)
P("in-game-voice", "In-Game Voice", "Communication", "Typical game VOIP: 120 Hz cut, 3 kHz cut-through, ceiling so it is not shrill.", {
    0: hp(120), 3: pk(400, -2.0, 1.2), 6: pk(3000, 3.6, 1.0), 9: lp(12000),
}, -0.3)
P("male-comms", "Male Comms", "Communication", "Chest control at 240 Hz, diction at 2.5 kHz.", {
    0: hp(80), 2: pk(140, 1.0, 1.1), 3: pk(240, -2.4, 1.4), 6: pk(2500, 2.8, 1.15), 8: hs(10000, 1.2, 0.8),
}, -0.3)
P("female-comms", "Female Comms", "Communication", "De-mud 280 Hz, presence 5 kHz, air without sizzle.", {
    0: hp(95), 3: pk(280, -2.6, 1.3), 6: pk(3200, 1.6, 1.3), 7: pk(5200, 2.6, 1.15), 8: hs(12000, 1.6, 0.8),
}, -0.3)
P("quiet-talkers", "Quiet Talkers", "Communication", "Push 2–4 kHz and a bit of 1.2 kHz so low talkers read.", {
    0: hp(100), 3: pk(300, -1.8, 1.2), 5: pk(1200, 1.8, 1.1), 6: pk(2800, 4.0, 1.05), 7: pk(4500, 2.2, 1.2),
}, -0.6)
P("noisy-lobby", "Noisy Lobby", "Communication", "Tight HPF, scoop 400–800, strong 3 kHz so callouts beat the crowd.", {
    0: hp(140), 3: pk(400, -3.2, 1.3), 4: pk(700, -2.0, 1.2), 6: pk(3200, 4.2, 1.1),
}, -0.4)
P("raid-call", "Raid / Stack Call", "Communication", "Many voices: de-box, 2 kHz intelligibility, tamed 6 kHz.", {
    0: hp(110), 3: pk(300, -2.8, 1.25), 6: pk(2000, 3.0, 1.05), 7: pk(6000, -1.6, 1.3),
}, -0.3)
P("stream-talk", "Stream / Broadcast", "Communication", "Radio-ready: rumble cut, 3 kHz cut-through, 12 kHz ceiling.", {
    0: hp(90), 3: pk(400, -2.0, 1.2), 6: pk(3000, 3.2, 1.0), 9: lp(12000),
}, -0.3)
P("podcast", "Podcast Voice", "Communication", "Broadcast HPF, de-boom, speech presence.", {
    0: hp(80, 0.8), 2: pk(150, -1.5, 1.2), 3: pk(350, -2.8, 1.3), 6: pk(2700, 2.6, 1.1), 8: hs(9000, 1.2, 0.8),
}, -0.2)
P("speech-intel", "Speech Intelligibility", "Communication", "Consonant lift at 2–4 kHz, low-mid cleanup.", {
    0: hp(100), 3: pk(300, -2.4, 1.4), 6: pk(2200, 3.6, 1.15), 7: pk(4000, 1.8, 1.2),
}, -0.5)
P("de-ess", "De-Sibilance", "Communication", "Keep 3 kHz words, cut 6–8 kHz hiss.", {
    0: hp(90), 6: pk(3000, 2.2, 1.2), 7: pk(7000, -3.8, 1.8),
})
P("proximity", "Close Mic / Breathing", "Communication", "HPF 140, cut 200 Hz pops, keep 4 kHz.", {
    0: hp(140), 2: pk(200, -3.5, 1.5), 7: pk(4500, 2.0, 1.2),
}, 0.3)
P("bluetooth-call", "Phone / Bluetooth", "Communication", "Fill out a thin remote voice.", {
    1: ls(200, 3.5, 0.8), 5: pk(1200, 1.5, 1.0), 8: hs(8000, 2.0, 0.8),
}, -0.8)

# --- Games ---
P("fps-competitive", "FPS Competitive", "Games", "Cut explosion bass, boost 2–4 kHz footsteps and info. The default try for ranked.", {
    0: hp(55), 1: ls(70, -3.5, 0.8), 3: pk(300, -2.0, 1.2), 5: pk(1800, 1.6, 1.2), 6: pk(3200, 3.8, 1.05), 7: pk(5000, 2.4, 1.15), 8: hs(12000, 1.0, 0.8),
}, 0.4)
P("fps-footsteps", "FPS Footsteps", "Games", "200–400 Hz body plus 3–6 kHz transients for steps, reloads, and cloth.", {
    0: hp(50), 1: ls(80, -2.0, 0.8), 2: pk(220, 2.4, 1.3), 3: pk(380, 1.6, 1.4), 6: pk(3000, 3.2, 1.2), 7: pk(6000, 2.8, 1.2),
}, 0.2)
P("valorant-cs", "Valorant / CS", "Games", "Thin, dry, info-first. Little sub, lots of 2–5 kHz.", {
    0: hp(70), 1: ls(90, -4.0, 0.75), 3: pk(350, -1.8, 1.2), 6: pk(2800, 3.6, 1.1), 7: pk(4800, 2.6, 1.15), 8: hs(11000, 0.8, 0.8),
}, 0.6)
P("cod-apex", "CoD / Apex", "Games", "Keep some gun punch, still lift footsteps and suppress rumble.", {
    0: hp(40), 1: ls(65, -1.5, 0.85), 2: pk(140, 1.2, 1.1), 3: pk(280, -2.2, 1.3), 6: pk(3500, 3.0, 1.1), 7: pk(5500, 1.8, 1.2),
})
P("battle-royale", "Battle Royale", "Games", "Long-range info: 4 kHz lift, less 80 Hz thump so you hear rotos and steps.", {
    0: hp(45), 1: ls(80, -2.8, 0.8), 4: pk(700, -1.0, 1.0), 6: pk(2500, 2.2, 1.15), 7: pk(4500, 3.2, 1.1), 8: hs(10000, 1.4, 0.75),
}, 0.3)
P("warzone", "Warzone / Big Map", "Games", "Vehicles and nades down, footsteps and UAV-style detail up.", {
    0: hp(50), 1: ls(55, -4.0, 0.85), 2: pk(120, -1.5, 1.1), 6: pk(3000, 3.4, 1.1), 7: pk(6500, 2.2, 1.2),
}, 0.5)
P("explosions-down", "Explosions Down", "Games", "Park the LFE and 100 Hz bloom so you are not deaf after every nade.", {
    0: hp(40), 1: ls(70, -5.5, 0.7), 2: pk(110, -3.0, 1.2), 7: pk(5000, -1.2, 1.3),
}, 1.2)
P("night-ops", "Night Ops", "Games", "Quiet maps: lift 2–8 kHz cues, keep a little sub for atmosphere.", {
    1: ls(80, -1.0, 0.8), 5: pk(1500, 1.4, 1.1), 6: pk(2800, 2.8, 1.15), 7: pk(7000, 2.4, 1.1), 8: hs(12000, 1.6, 0.7),
})
P("tactical", "Tactical / Slow Push", "Games", "Footstep body at 250 Hz, whisper-range 4 kHz, controlled bass.", {
    0: hp(50), 1: ls(75, -2.4, 0.8), 3: pk(250, 2.0, 1.35), 7: pk(4200, 3.4, 1.15),
})
P("horror", "Horror / Stealth", "Games", "Creaks and breaths: 3–8 kHz, less mud, enough low end for stingers.", {
    0: hp(35), 3: pk(400, -2.0, 1.1), 6: pk(3200, 2.6, 1.2), 7: pk(7500, 2.8, 1.1), 8: hs(12000, 1.2, 0.75),
})
P("open-world", "Open World / MMO", "Games", "Keep music and ambience; a little presence so UI and VO read.", {
    0: hp(32), 1: ls(70, 1.2, 0.8), 3: pk(300, -1.0, 1.1), 6: pk(2500, 1.6, 1.1), 8: hs(12000, 1.4, 0.75),
}, -0.3)
P("cinematic-sp", "Cinematic Single-Player", "Games", "Keep LFE and score. Soft 3 kHz so cutscenes are not harsh.", {
    1: ls(55, 2.4, 0.8), 6: pk(3000, -1.4, 1.2), 8: hs(10000, 1.2, 0.75),
}, -0.5)
P("immersive-bass", "Immersive Bass", "Games", "Single-player thump: 50–80 Hz up, 300 Hz cleaned.", {
    1: ls(55, 4.0, 0.85), 3: pk(300, -2.4, 1.3), 8: hs(11000, 1.0, 0.8),
}, -1.0)
P("racing", "Racing", "Games", "Engine body 120–200 Hz, tame 4 kHz exhaust harshness.", {
    0: hp(35), 2: pk(160, 2.2, 1.1), 7: pk(4000, -2.4, 1.3), 8: hs(12000, 1.0, 0.8),
})
P("flight-sim", "Flight Sim", "Games", "Rumble cut, radio-ish 2 kHz, less cabin roar at 200 Hz.", {
    0: hp(45), 2: pk(200, -2.8, 1.2), 6: pk(2200, 2.4, 1.1), 9: lp(14000),
})
P("fighting", "Fighting Game", "Games", "Hit confirms at 2–5 kHz, keep some bass for impacts.", {
    1: ls(80, 1.6, 0.85), 3: pk(350, -1.2, 1.1), 6: pk(2500, 2.4, 1.15), 7: pk(5000, 2.8, 1.1),
}, -0.4)
P("sports", "Sports", "Games", "Crowd down a bit, commentary/PA lane at 2–4 kHz.", {
    2: pk(180, -1.4, 1.0), 4: pk(600, -1.6, 1.0), 6: pk(2800, 2.8, 1.1),
})
P("retro", "Retro / Arcade", "Games", "Small-speaker character: no sub, mid forward.", {
    0: hp(120), 5: pk(1400, 2.2, 0.9), 9: lp(11000),
}, 0.6)
P("headset-fps", "Headset FPS", "Games", "Typical gaming headset: less 80 Hz bloom, more 3 kHz and 8 kHz.", {
    1: ls(80, -2.8, 0.75), 3: pk(250, -1.6, 1.2), 6: pk(3000, 3.4, 1.1), 8: hs(8000, 2.0, 0.75),
}, 0.3)
P("competitive-thin", "Competitive Thin", "Games", "Aggressive rumble cut and mid scoop for maximum positional cues.", {
    0: hp(80), 1: ls(100, -3.5, 0.7), 4: pk(600, -3.0, 0.9), 6: pk(3500, 4.2, 1.05), 7: pk(6000, 2.0, 1.2),
}, 0.8)

# --- Hybrid (game + voice / music + chat) ---
P("game-plus-voice", "Game + Team Voice", "Hybrid", "Footstep 3 kHz and a reserved 2–4 kHz lane so teammates stay on top of the mix.", {
    0: hp(55), 1: ls(70, -2.2, 0.8), 3: pk(300, -2.2, 1.25), 5: pk(1500, -0.8, 1.0), 6: pk(2800, 3.6, 1.05), 7: pk(4500, 2.2, 1.15), 8: hs(11000, 1.0, 0.8),
}, 0.2)
P("ranked-plus-comms", "Ranked + Comms", "Hybrid", "Valorant-thin game EQ with extra 2.5 kHz for Discord/in-game voice.", {
    0: hp(70), 1: ls(85, -3.6, 0.75), 3: pk(340, -2.0, 1.2), 6: pk(2500, 4.0, 1.05), 7: pk(5000, 2.4, 1.15),
}, 0.5)
P("music-plus-discord", "Music + Discord", "Hybrid", "Keep a music smile, duck 400 Hz mud, lift 3 kHz so chat sits above the track.", {
    1: ls(70, 2.0, 0.8), 3: pk(400, -2.4, 1.2), 6: pk(3000, 3.0, 1.1), 8: hs(11000, 1.6, 0.75),
}, -0.5)
P("stream-monitor", "Stream Monitor", "Hybrid", "Game + chat + music: rumble cut, voice lane, silk without ear fatigue.", {
    0: hp(40), 1: ls(80, -1.2, 0.8), 3: pk(320, -1.8, 1.2), 6: pk(2700, 2.8, 1.1), 7: pk(6000, -1.0, 1.4), 8: hs(12000, 1.2, 0.75),
})
P("cinematic-plus-vo", "Cinematic + Dialogue", "Hybrid", "Keep score and LFE, carve 2–4 kHz so story VO and party chat read.", {
    1: ls(60, 1.8, 0.8), 3: pk(280, -1.4, 1.1), 6: pk(3000, 2.6, 1.1), 8: hs(12000, 1.0, 0.75),
}, -0.4)
P("night-plus-comms", "Night Game + Comms", "Hybrid", "Low-volume loudness plus a speech bump for late sessions.", {
    1: ls(75, 1.6, 0.75), 5: pk(1400, -1.0, 0.9), 6: pk(2800, 3.4, 1.05), 8: hs(8500, 1.8, 0.8),
}, -0.6)
P("party-hybrid", "Party Game", "Hybrid", "Fun bass for the lobby, 3 kHz so callouts still land.", {
    1: ls(65, 3.4, 0.8), 3: pk(300, -1.8, 1.2), 6: pk(3000, 2.8, 1.1), 8: hs(10000, 1.6, 0.75),
}, -0.8)
P("movie-plus-chat", "Movie + Voice Chat", "Hybrid", "Home-theater bass, dialogue 3 kHz, Discord still audible.", {
    1: ls(50, 2.8, 0.8), 3: pk(250, -1.2, 1.1), 6: pk(3200, 2.4, 1.1), 8: hs(10000, 1.2, 0.75),
}, -0.6)
P("mmo-plus-raid", "MMO + Raid Call", "Hybrid", "Ambience intact, 2 kHz raid-call lane, less 6 kHz clash.", {
    0: hp(35), 1: ls(80, 1.0, 0.8), 3: pk(350, -1.6, 1.15), 6: pk(2100, 3.2, 1.05), 7: pk(6200, -1.4, 1.3),
}, -0.2)
P("br-plus-squad", "BR + Squad", "Hybrid", "Battle-royale info EQ with extra 2.7 kHz for squad VOIP.", {
    0: hp(48), 1: ls(75, -2.6, 0.8), 6: pk(2700, 3.8, 1.05), 7: pk(4800, 2.4, 1.15), 8: hs(10000, 1.2, 0.75),
}, 0.3)
P("sim-plus-atc", "Sim + ATC", "Hybrid", "Cabin roar down, radio-voice 2 kHz up.", {
    0: hp(50), 2: pk(180, -3.0, 1.15), 6: pk(2000, 3.4, 1.1), 9: lp(13000),
})
P("low-volume-hybrid", "Low Volume Hybrid", "Hybrid", "Quiet-night contour plus speech so game and chat both survive low master volume.", {
    1: ls(80, 2.8, 0.75), 3: pk(350, -1.4, 1.1), 6: pk(2600, 3.2, 1.05), 8: hs(9000, 2.0, 0.8),
}, -0.8)
P("headset-hybrid", "Headset Hybrid", "Hybrid", "Gaming headset: less bloom, footsteps + teammates in the same 3 kHz window.", {
    1: ls(85, -2.2, 0.75), 3: pk(280, -1.8, 1.2), 6: pk(3000, 3.6, 1.05), 8: hs(8500, 1.6, 0.75),
}, 0.2)

if __name__ == "__main__":
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent / "presets.json"
    path.write_text(json.dumps(PRESETS, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    c = Counter(p["category"] for p in PRESETS)
    print(len(PRESETS), "presets", dict(c))
    print("wrote", path)
