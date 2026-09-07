/** ISO-ish 10-band parametric factory library. */

export const FILTER_TYPES = [
  { id: "highpass", label: "HP" },
  { id: "lowshelf", label: "LS" },
  { id: "peaking", label: "Peak" },
  { id: "notch", label: "Notch" },
  { id: "highshelf", label: "HS" },
  { id: "lowpass", label: "LP" },
];

export const TYPE_LABELS = {
  highpass: "High-pass",
  lowshelf: "Low shelf",
  peaking: "Peaking",
  notch: "Notch",
  highshelf: "High shelf",
  lowpass: "Low-pass",
};

export function defaultBands() {
  return [
    band("highpass", 20, 0, 0.71, false),
    band("lowshelf", 80, 0, 0.85, false),
    band("peaking", 160, 0, 1.1, false),
    band("peaking", 350, 0, 1.05, false),
    band("peaking", 700, 0, 1.0, false),
    band("peaking", 1500, 0, 1.0, false),
    band("peaking", 3000, 0, 1.1, false),
    band("peaking", 5500, 0, 1.15, false),
    band("highshelf", 10000, 0, 0.85, false),
    band("lowpass", 20000, 0, 0.71, false),
  ];
}

function band(type, frequency, gain, q, enabled = true) {
  return { type, frequency, gain, q, enabled };
}

function cloneBands(src) {
  return src.map((b) => ({ ...b }));
}

function apply(patches) {
  const bands = defaultBands();
  for (const [i, patch] of Object.entries(patches)) {
    Object.assign(bands[Number(i)], patch, { enabled: patch.enabled !== false });
  }
  return bands;
}

function P(id, name, category, description, patches, outputGain = 0) {
  return { id, name, category, description, bands: apply(patches), outputGain };
}

export const CATEGORIES = [
  "All",
  "Init",
  "Vocal",
  "Podcast",
  "Mix & Master",
  "Bass",
  "Drums",
  "Guitar",
  "Keys",
  "Electronic",
  "Genre",
  "Character",
  "Playback",
  "Utility",
];

export const PRESETS = [
  P("flat", "Flat Reference", "Init", "Unity gain. All bands parked and silent.", {}, 0),

  P("female-lead", "Female Lead", "Vocal", "HPF 90 Hz, de-mud 280, presence 5 kHz, air shelf.", {
    0: { frequency: 90, q: 0.8, enabled: true },
    3: { frequency: 280, gain: -2.5, q: 1.3 },
    6: { frequency: 3200, gain: 1.8, q: 1.4 },
    7: { frequency: 5200, gain: 2.8, q: 1.2 },
    8: { frequency: 12000, gain: 2.2, q: 0.8 },
  }, -0.4),
  P("male-lead", "Male Lead", "Vocal", "Chest weight, 200 Hz control, 2.5 kHz diction.", {
    0: { frequency: 80, q: 0.75, enabled: true },
    2: { frequency: 140, gain: 1.4, q: 1.1 },
    3: { frequency: 240, gain: -2.2, q: 1.4 },
    6: { frequency: 2500, gain: 2.4, q: 1.2 },
    8: { frequency: 11000, gain: 1.6, q: 0.8 },
  }, -0.3),
  P("vocal-air", "Vocal Air", "Vocal", "Gentle presence and an open 12 kHz shelf.", {
    0: { frequency: 85, enabled: true },
    7: { frequency: 6000, gain: 1.5, q: 1.3 },
    8: { frequency: 12500, gain: 3.2, q: 0.75 },
  }, -0.5),
  P("vocal-presence", "Vocal Presence", "Vocal", "Forward 4–5 kHz without harshness.", {
    0: { frequency: 100, enabled: true },
    4: { frequency: 800, gain: -1.2, q: 1.1 },
    6: { frequency: 2800, gain: 1.5, q: 1.3 },
    7: { frequency: 4500, gain: 3.4, q: 1.15 },
  }, -0.6),
  P("harmony-stack", "Harmony Stack", "Vocal", "Tuck body, add sheen so stacks sit behind a lead.", {
    0: { frequency: 140, enabled: true },
    2: { frequency: 220, gain: -2.8, q: 1.1 },
    7: { frequency: 7000, gain: 2.0, q: 1.0 },
    8: { frequency: 13000, gain: 1.5, q: 0.8 },
  }),
  P("rap-vocal", "Rap Vocal", "Vocal", "Intelligibility bump at 2 kHz, tight low cut.", {
    0: { frequency: 110, q: 0.85, enabled: true },
    3: { frequency: 300, gain: -2.0, q: 1.2 },
    6: { frequency: 2000, gain: 3.0, q: 1.1 },
    7: { frequency: 5000, gain: 1.4, q: 1.3 },
  }, -0.4),
  P("choir-lift", "Choir Lift", "Vocal", "Open hall of voices — high-pass, 4 kHz bloom, air.", {
    0: { frequency: 120, enabled: true },
    5: { frequency: 1600, gain: -1.0, q: 1.0 },
    7: { frequency: 4200, gain: 2.2, q: 1.0 },
    8: { frequency: 14000, gain: 2.5, q: 0.7 },
  }),
  P("de-mud-vocal", "De-Mud Vocal", "Vocal", "Surgical cut around 250–400 Hz boxiness.", {
    0: { frequency: 80, enabled: true },
    3: { frequency: 260, gain: -4.0, q: 1.8 },
    4: { frequency: 450, gain: -1.8, q: 1.4 },
  }, 0.6),

  P("podcast-voice", "Podcast Voice", "Podcast", "Broadcast HPF, de-boom, speech presence.", {
    0: { frequency: 80, q: 0.8, enabled: true },
    2: { frequency: 150, gain: -1.5, q: 1.2 },
    3: { frequency: 350, gain: -2.8, q: 1.3 },
    6: { frequency: 2700, gain: 2.6, q: 1.1 },
    8: { frequency: 9000, gain: 1.2, q: 0.8 },
  }, -0.2),
  P("broadcast-chain", "Broadcast Chain", "Podcast", "Radio-ready: rumble cut, 3 kHz cut-through, ceiling.", {
    0: { frequency: 90, enabled: true },
    3: { frequency: 400, gain: -2.0, q: 1.2 },
    6: { frequency: 3000, gain: 3.2, q: 1.0 },
    9: { frequency: 12000, q: 0.7, enabled: true },
  }, -0.3),
  P("speech-intel", "Speech Intelligibility", "Podcast", "Consonant lift at 2–4 kHz, low-mid cleanup.", {
    0: { frequency: 100, enabled: true },
    3: { frequency: 300, gain: -2.4, q: 1.4 },
    6: { frequency: 2200, gain: 3.6, q: 1.15 },
    7: { frequency: 4000, gain: 1.8, q: 1.2 },
  }, -0.5),
  P("warm-narration", "Warm Narration", "Podcast", "Audiobook body with a polite top.", {
    0: { frequency: 70, enabled: true },
    2: { frequency: 180, gain: 2.2, q: 1.0 },
    7: { frequency: 6000, gain: -1.5, q: 1.0 },
    8: { frequency: 10000, gain: -1.0, q: 0.8 },
  }),
  P("phone-in", "Phone-In Clean", "Podcast", "Make a thin remote voice sound fuller.", {
    1: { frequency: 200, gain: 3.5, q: 0.8 },
    5: { frequency: 1200, gain: 1.5, q: 1.0 },
    8: { frequency: 8000, gain: 2.0, q: 0.8 },
  }, -0.8),

  P("mixbus-glue", "Mixbus Glue", "Mix & Master", "Subtle smiley, 250 Hz tuck, 10 kHz silk.", {
    1: { frequency: 90, gain: 1.2, q: 0.75 },
    3: { frequency: 250, gain: -1.2, q: 1.1 },
    7: { frequency: 5000, gain: 0.8, q: 1.0 },
    8: { frequency: 11000, gain: 1.4, q: 0.75 },
  }, -0.4),
  P("master-clarity", "Master Clarity", "Mix & Master", "HPF 30 Hz, 400 Hz dip, 3 kHz and air.", {
    0: { frequency: 30, q: 0.7, enabled: true },
    4: { frequency: 400, gain: -1.4, q: 1.2 },
    6: { frequency: 3000, gain: 1.3, q: 1.3 },
    8: { frequency: 14000, gain: 1.8, q: 0.7 },
  }, -0.3),
  P("warm-master", "Warm Master", "Mix & Master", "Low shelf weight, rolled air, analog body.", {
    1: { frequency: 100, gain: 1.8, q: 0.8 },
    5: { frequency: 1800, gain: -0.8, q: 1.0 },
    8: { frequency: 12000, gain: -1.6, q: 0.7 },
    9: { frequency: 16000, enabled: true },
  }),
  P("loudness-lift", "Loudness Lift", "Mix & Master", "Fletcher-Munson contour for quieter playback.", {
    1: { frequency: 80, gain: 3.2, q: 0.75 },
    5: { frequency: 1400, gain: -1.5, q: 0.9 },
    8: { frequency: 9000, gain: 2.4, q: 0.8 },
  }, -1.0),
  P("streaming-curve", "Streaming Curve", "Mix & Master", "Translation-friendly slight U with a safe HPF.", {
    0: { frequency: 28, enabled: true },
    1: { frequency: 70, gain: 0.8, q: 0.8 },
    4: { frequency: 600, gain: -0.6, q: 1.0 },
    8: { frequency: 12000, gain: 1.1, q: 0.75 },
  }),
  P("analog-console", "Analog Console", "Mix & Master", "Neve-ish weight at 200 Hz, presence at 5 kHz.", {
    1: { frequency: 60, gain: 1.5, q: 0.8 },
    2: { frequency: 200, gain: 1.8, q: 1.0 },
    7: { frequency: 5000, gain: 2.0, q: 1.1 },
    8: { frequency: 10000, gain: 0.8, q: 0.8 },
  }, -0.8),
  P("ssl-bus", "SSL-ish Bus", "Mix & Master", "Classic mixbus: high-pass, 6–8 kHz bite, air.", {
    0: { frequency: 40, enabled: true },
    3: { frequency: 350, gain: -0.8, q: 1.0 },
    7: { frequency: 6500, gain: 2.4, q: 1.0 },
    8: { frequency: 12000, gain: 1.6, q: 0.7 },
  }, -0.5),
  P("vinyl-master", "Vinyl Master", "Mix & Master", "Rumble cut, elliptical-ish low, softened top.", {
    0: { frequency: 35, q: 0.8, enabled: true },
    2: { frequency: 120, gain: -1.0, q: 1.1 },
    8: { frequency: 14000, gain: -1.8, q: 0.7 },
    9: { frequency: 18000, enabled: true },
  }),

  P("sub-focus", "Sub Focus", "Bass", "Concentrate energy at 50–70 Hz, clean the 250 Hz bloom.", {
    0: { frequency: 28, enabled: true },
    1: { frequency: 55, gain: 3.4, q: 1.0 },
    3: { frequency: 250, gain: -3.2, q: 1.4 },
    9: { frequency: 8000, enabled: true },
  }, -0.6),
  P("tight-bass", "Tight Bass", "Bass", "HPF 40 Hz, scoop 300, pick attack at 800 Hz.", {
    0: { frequency: 40, q: 0.8, enabled: true },
    3: { frequency: 300, gain: -3.5, q: 1.5 },
    4: { frequency: 800, gain: 2.2, q: 1.2 },
    6: { frequency: 2500, gain: 1.0, q: 1.3 },
  }),
  P("808-curve", "808 Curve", "Bass", "Sub shelf, 80 Hz bump, 1 kHz click, dark top.", {
    1: { frequency: 45, gain: 4.5, q: 0.9 },
    2: { frequency: 80, gain: 2.0, q: 1.4 },
    5: { frequency: 1000, gain: 2.4, q: 1.5 },
    9: { frequency: 5000, enabled: true },
  }, -1.2),
  P("upright-bass", "Upright Bass", "Bass", "Wood at 120 Hz, string at 800, airless and close.", {
    0: { frequency: 45, enabled: true },
    2: { frequency: 120, gain: 2.4, q: 1.1 },
    4: { frequency: 800, gain: 1.8, q: 1.2 },
    8: { frequency: 8000, gain: -2.5, q: 0.8 },
  }),
  P("synth-bass", "Synth Bass", "Bass", "Fundamental boost, 2 kHz growl, low-pass dirt.", {
    1: { frequency: 70, gain: 2.8, q: 0.9 },
    5: { frequency: 900, gain: 1.6, q: 1.1 },
    6: { frequency: 2200, gain: 2.8, q: 1.3 },
    9: { frequency: 6500, q: 0.8, enabled: true },
  }, -0.8),
  P("bass-presence", "Bass Presence", "Bass", "Let a bass cut through a dense mix at 1–1.5 kHz.", {
    0: { frequency: 35, enabled: true },
    3: { frequency: 280, gain: -2.0, q: 1.2 },
    5: { frequency: 1300, gain: 3.2, q: 1.15 },
  }),

  P("kick-punch", "Kick Punch", "Drums", "Click at 3.5 kHz, punch at 60, de-box 300.", {
    1: { frequency: 60, gain: 3.0, q: 1.1 },
    3: { frequency: 300, gain: -3.8, q: 1.6 },
    6: { frequency: 3500, gain: 3.4, q: 1.3 },
    9: { frequency: 12000, enabled: true },
  }, -0.5),
  P("snare-crack", "Snare Crack", "Drums", "Body 200 Hz, crack 5 kHz, air 10 kHz.", {
    0: { frequency: 80, enabled: true },
    2: { frequency: 200, gain: 2.2, q: 1.2 },
    7: { frequency: 5200, gain: 4.0, q: 1.2 },
    8: { frequency: 11000, gain: 2.0, q: 0.8 },
  }, -0.8),
  P("overhead-air", "Overhead Air", "Drums", "HPF 80, cymbal silk, reduced stick at 400.", {
    0: { frequency: 90, enabled: true },
    4: { frequency: 400, gain: -2.2, q: 1.1 },
    8: { frequency: 13000, gain: 3.0, q: 0.7 },
  }),
  P("room-depth", "Room Depth", "Drums", "Leave the bloom, cut rumble, tame 2 kHz harsh.", {
    0: { frequency: 70, enabled: true },
    2: { frequency: 160, gain: 1.8, q: 1.0 },
    6: { frequency: 2200, gain: -2.5, q: 1.2 },
    8: { frequency: 10000, gain: 1.4, q: 0.8 },
  }),
  P("drum-bus", "Drum Bus", "Drums", "Weight, 400 Hz clean, 8 kHz sheen.", {
    0: { frequency: 35, enabled: true },
    1: { frequency: 80, gain: 1.6, q: 0.85 },
    4: { frequency: 400, gain: -1.8, q: 1.2 },
    8: { frequency: 8000, gain: 2.2, q: 0.8 },
  }, -0.4),
  P("lofi-drums", "Lo-fi Drums", "Drums", "Band-limited, mid forward, no air.", {
    0: { frequency: 80, enabled: true },
    5: { frequency: 1200, gain: 2.0, q: 0.9 },
    9: { frequency: 6500, q: 0.8, enabled: true },
  }),

  P("acoustic-sparkle", "Acoustic Sparkle", "Guitar", "HPF 70, 2.5 kHz pick, 12 kHz air.", {
    0: { frequency: 70, enabled: true },
    3: { frequency: 250, gain: -2.0, q: 1.2 },
    6: { frequency: 2500, gain: 2.4, q: 1.2 },
    8: { frequency: 12000, gain: 2.6, q: 0.75 },
  }, -0.4),
  P("electric-rhythm", "Electric Rhythm", "Guitar", "Cut boom, 1.2 kHz body, 3.5 kHz bite.", {
    0: { frequency: 90, enabled: true },
    3: { frequency: 220, gain: -2.8, q: 1.3 },
    5: { frequency: 1200, gain: 1.8, q: 1.1 },
    6: { frequency: 3500, gain: 2.6, q: 1.2 },
  }),
  P("distorted-cut", "Distorted Cut", "Guitar", "Scoop mids slightly, add 4 kHz so it slices.", {
    0: { frequency: 100, enabled: true },
    4: { frequency: 500, gain: -2.2, q: 1.0 },
    5: { frequency: 900, gain: -1.4, q: 1.1 },
    7: { frequency: 4200, gain: 3.0, q: 1.15 },
  }),
  P("clean-jazz", "Clean Jazz", "Guitar", "Warm neck pickup: 200 Hz body, rolled treble.", {
    2: { frequency: 180, gain: 2.0, q: 1.0 },
    7: { frequency: 5000, gain: -2.0, q: 0.9 },
    8: { frequency: 9000, gain: -2.5, q: 0.8 },
  }),
  P("strum-body", "Strum Body", "Guitar", "Full strums without mud — 120 Hz up, 300 Hz down.", {
    0: { frequency: 80, enabled: true },
    2: { frequency: 120, gain: 1.8, q: 1.1 },
    3: { frequency: 320, gain: -2.6, q: 1.4 },
    8: { frequency: 10000, gain: 1.5, q: 0.8 },
  }),

  P("piano-concert", "Piano Concert", "Keys", "Lid-open: 80 Hz weight, 3 kHz hammers, air.", {
    0: { frequency: 35, enabled: true },
    1: { frequency: 80, gain: 1.4, q: 0.8 },
    4: { frequency: 400, gain: -1.0, q: 1.1 },
    6: { frequency: 3000, gain: 1.8, q: 1.2 },
    8: { frequency: 12000, gain: 2.0, q: 0.7 },
  }, -0.3),
  P("rhodes-warmth", "Rhodes Warmth", "Keys", "Bell tines at 2 kHz, bass fat, dark top.", {
    1: { frequency: 90, gain: 2.4, q: 0.85 },
    6: { frequency: 2200, gain: 2.2, q: 1.3 },
    8: { frequency: 8000, gain: -2.0, q: 0.8 },
  }),
  P("synth-pad", "Synth Pad", "Keys", "Remove rumble, widen with 8–12 kHz silk.", {
    0: { frequency: 80, enabled: true },
    3: { frequency: 300, gain: -1.5, q: 1.0 },
    8: { frequency: 11000, gain: 2.8, q: 0.7 },
  }),
  P("organ-church", "Organ Church", "Keys", "Pedal fundamental, 800 Hz growl, gentle air.", {
    1: { frequency: 60, gain: 2.6, q: 0.9 },
    4: { frequency: 800, gain: 1.8, q: 1.1 },
    8: { frequency: 10000, gain: 1.0, q: 0.8 },
  }),

  P("edm-drop", "EDM Drop", "Electronic", "Sub, 4 kHz aggression, air for white-noise risers.", {
    1: { frequency: 50, gain: 3.6, q: 0.9 },
    3: { frequency: 280, gain: -2.0, q: 1.2 },
    7: { frequency: 4000, gain: 2.8, q: 1.1 },
    8: { frequency: 13000, gain: 2.2, q: 0.7 },
  }, -1.0),
  P("house-groove", "House Groove", "Electronic", "Punchy kick lane, warm mids, disco top.", {
    1: { frequency: 65, gain: 2.2, q: 1.0 },
    4: { frequency: 500, gain: -1.2, q: 1.0 },
    8: { frequency: 10000, gain: 2.4, q: 0.75 },
  }),
  P("techno-body", "Techno Body", "Electronic", "Hard HPF, mid emphasis, controlled air.", {
    0: { frequency: 40, enabled: true },
    2: { frequency: 130, gain: 1.6, q: 1.2 },
    5: { frequency: 1600, gain: 1.4, q: 1.1 },
    8: { frequency: 12000, gain: 1.0, q: 0.8 },
  }),
  P("ambient-space", "Ambient Space", "Electronic", "Deep HPF, scooped mids, halo of air.", {
    0: { frequency: 60, enabled: true },
    4: { frequency: 700, gain: -2.4, q: 0.9 },
    8: { frequency: 14000, gain: 3.4, q: 0.65 },
  }),

  P("rock-mix", "Rock Mix", "Genre", "Tight bottom, 2.5 kHz attitude, cymbal air.", {
    0: { frequency: 40, enabled: true },
    3: { frequency: 300, gain: -1.6, q: 1.1 },
    6: { frequency: 2500, gain: 2.2, q: 1.1 },
    8: { frequency: 11000, gain: 1.8, q: 0.75 },
  }, -0.4),
  P("jazz-club", "Jazz Club", "Genre", "Warm room: 150 Hz body, soft presence, no hype.", {
    1: { frequency: 80, gain: 1.2, q: 0.8 },
    2: { frequency: 160, gain: 1.4, q: 1.0 },
    7: { frequency: 5000, gain: 0.8, q: 1.0 },
    8: { frequency: 12000, gain: -0.8, q: 0.8 },
  }),
  P("hip-hop", "Hip-Hop", "Genre", "Sub-heavy, vocal lane at 3 kHz, crisp hats.", {
    1: { frequency: 50, gain: 3.8, q: 0.9 },
    4: { frequency: 500, gain: -1.4, q: 1.0 },
    6: { frequency: 3000, gain: 1.8, q: 1.2 },
    8: { frequency: 10000, gain: 2.0, q: 0.8 },
  }, -1.0),
  P("metal-scoop", "Metal Scoop", "Genre", "Classic V: sub + 80 Hz, deep mid scoop, razor 4–6 k.", {
    1: { frequency: 70, gain: 2.8, q: 1.0 },
    4: { frequency: 600, gain: -4.5, q: 1.0 },
    5: { frequency: 1100, gain: -3.0, q: 1.1 },
    7: { frequency: 5500, gain: 3.6, q: 1.1 },
  }, 0.4),
  P("classical-hall", "Classical Hall", "Genre", "Natural: rumble cut, 2 kHz sheen, open air.", {
    0: { frequency: 32, enabled: true },
    6: { frequency: 2500, gain: 1.0, q: 1.2 },
    8: { frequency: 14000, gain: 1.6, q: 0.7 },
  }),
  P("pop-radio", "Pop Radio", "Genre", "Loudness-friendly smile and vocal presence.", {
    1: { frequency: 90, gain: 1.8, q: 0.8 },
    3: { frequency: 300, gain: -1.2, q: 1.1 },
    6: { frequency: 2800, gain: 2.0, q: 1.15 },
    8: { frequency: 11000, gain: 2.2, q: 0.75 },
  }, -0.6),
  P("rnb-smooth", "R&B Smooth", "Genre", "Warm 100 Hz, silky 8 kHz, polite mids.", {
    1: { frequency: 100, gain: 2.2, q: 0.8 },
    5: { frequency: 1500, gain: -1.0, q: 1.0 },
    8: { frequency: 8000, gain: 2.4, q: 0.75 },
  }),
  P("country-acoustic", "Country Acoustic", "Genre", "Storyteller vocal/guitar lane, tidy low end.", {
    0: { frequency: 70, enabled: true },
    3: { frequency: 250, gain: -1.8, q: 1.2 },
    6: { frequency: 3200, gain: 2.0, q: 1.1 },
    8: { frequency: 10000, gain: 1.6, q: 0.8 },
  }),
  P("reggae-bass", "Reggae Bass", "Genre", "Deep 50–80 Hz, scooped box, gentle top.", {
    1: { frequency: 55, gain: 3.4, q: 1.0 },
    3: { frequency: 300, gain: -2.8, q: 1.3 },
    8: { frequency: 9000, gain: 1.0, q: 0.8 },
  }, -0.6),
  P("lofi-hiphop", "Lo-fi Hip-Hop", "Genre", "Vinyl bandwidth, warm mids, no sparkle.", {
    0: { frequency: 60, enabled: true },
    2: { frequency: 180, gain: 2.0, q: 1.0 },
    9: { frequency: 7500, q: 0.75, enabled: true },
  }),
  P("trap-808", "Trap 808", "Genre", "Sub monster with a 1 kHz knock.", {
    1: { frequency: 40, gain: 5.0, q: 0.95 },
    2: { frequency: 90, gain: 1.5, q: 1.4 },
    5: { frequency: 1100, gain: 2.8, q: 1.6 },
    9: { frequency: 6000, enabled: true },
  }, -1.4),
  P("indie-warmth", "Indie Warmth", "Genre", "Tape-like tilt: more 200 Hz, less 8 kHz.", {
    2: { frequency: 200, gain: 2.0, q: 0.9 },
    7: { frequency: 6000, gain: -1.6, q: 0.9 },
    8: { frequency: 12000, gain: -1.2, q: 0.8 },
  }),

  P("telephone", "Telephone", "Character", "Narrow 300–3200 Hz bandpass character.", {
    0: { frequency: 300, q: 0.9, enabled: true },
    9: { frequency: 3200, q: 0.9, enabled: true },
    6: { frequency: 1800, gain: 3.0, q: 1.0 },
  }, 2.5),
  P("am-radio", "AM Radio", "Character", "Mid-century radio: 150–5 kHz with honk.", {
    0: { frequency: 150, enabled: true },
    5: { frequency: 1200, gain: 3.5, q: 0.9 },
    9: { frequency: 5000, enabled: true },
  }, 1.5),
  P("megaphone", "Megaphone", "Character", "Harsh 1 kHz peak, no lows, no air.", {
    0: { frequency: 400, q: 0.8, enabled: true },
    5: { frequency: 1000, gain: 8.0, q: 1.6 },
    9: { frequency: 2800, q: 0.9, enabled: true },
  }, 0),
  P("cassette", "Cassette", "Character", "Woofer-less, 8 kHz ceiling, 200 Hz bump.", {
    0: { frequency: 50, enabled: true },
    2: { frequency: 180, gain: 1.8, q: 1.0 },
    9: { frequency: 9000, q: 0.7, enabled: true },
  }),
  P("vhs", "VHS", "Character", "Dark, small-speaker, 2 kHz nasal.", {
    0: { frequency: 90, enabled: true },
    6: { frequency: 2000, gain: 2.8, q: 1.4 },
    9: { frequency: 7000, enabled: true },
  }),
  P("underwater", "Underwater", "Character", "Extreme low-pass with a muffled 400 Hz bloom.", {
    3: { frequency: 400, gain: 3.0, q: 0.8 },
    9: { frequency: 700, q: 0.7, enabled: true },
  }, 1.2),
  P("stadium-pa", "Stadium PA", "Character", "Honky 800 Hz, no sub, harsh 3 kHz.", {
    0: { frequency: 120, enabled: true },
    4: { frequency: 800, gain: 4.5, q: 1.5 },
    6: { frequency: 3000, gain: 2.5, q: 1.3 },
    9: { frequency: 8000, enabled: true },
  }),
  P("small-speaker", "Small Speaker", "Character", "Laptop / Bluetooth: no sub, mid forward.", {
    0: { frequency: 180, enabled: true },
    5: { frequency: 1400, gain: 2.4, q: 0.9 },
    9: { frequency: 11000, enabled: true },
  }, 1.0),
  P("club-system", "Club System", "Character", "Huge sub and 50 Hz, scooped mids, bright hats.", {
    1: { frequency: 50, gain: 5.5, q: 0.9 },
    4: { frequency: 600, gain: -3.0, q: 1.0 },
    8: { frequency: 9000, gain: 2.5, q: 0.8 },
  }, -1.5),
  P("car-audio", "Car Audio", "Character", "Road-noise loudness: bass + presence.", {
    1: { frequency: 70, gain: 4.0, q: 0.8 },
    6: { frequency: 2500, gain: 2.0, q: 1.1 },
    8: { frequency: 10000, gain: 1.5, q: 0.8 },
  }, -1.2),
  P("walkie", "Walkie Talkie", "Character", "Aggressive band-limit and 2 kHz peak.", {
    0: { frequency: 500, q: 0.85, enabled: true },
    6: { frequency: 2000, gain: 6.0, q: 1.8 },
    9: { frequency: 3500, q: 0.9, enabled: true },
  }, 1.8),

  P("harman-ish", "Harman-ish", "Playback", "Consumer target: bass shelf and gentle treble.", {
    1: { frequency: 60, gain: 4.2, q: 0.7 },
    2: { frequency: 150, gain: 1.2, q: 0.9 },
    8: { frequency: 10000, gain: 2.4, q: 0.7 },
  }, -1.4),
  P("bass-boost", "Bass Boost", "Playback", "Broad low shelf, slight mid dip so it stays clean.", {
    1: { frequency: 80, gain: 6.0, q: 0.7 },
    4: { frequency: 500, gain: -1.2, q: 0.9 },
  }, -1.6),
  P("treble-boost", "Treble Boost", "Playback", "Open high shelf from 4 kHz.", {
    8: { frequency: 5000, gain: 4.5, q: 0.7 },
  }, -1.0),
  P("smiley", "Smiley", "Playback", "The classic U — bass, scooped mids, air.", {
    1: { frequency: 80, gain: 4.5, q: 0.75 },
    4: { frequency: 700, gain: -2.5, q: 0.9 },
    8: { frequency: 10000, gain: 4.0, q: 0.7 },
  }, -1.5),
  P("mid-scoop", "Mid Scoop", "Playback", "Wide 400–2 kHz cut for a hollow, wide feel.", {
    4: { frequency: 600, gain: -4.0, q: 0.8 },
    5: { frequency: 1600, gain: -3.2, q: 0.9 },
  }, 1.0),
  P("night-mode", "Night Mode", "Playback", "Less sub, more presence so it reads at low volume.", {
    1: { frequency: 70, gain: -3.5, q: 0.8 },
    6: { frequency: 2500, gain: 2.8, q: 1.0 },
    8: { frequency: 8000, gain: 1.8, q: 0.8 },
  }),
  P("presence-lift", "Presence Lift", "Playback", "2–6 kHz forward without extra bass.", {
    6: { frequency: 2500, gain: 2.4, q: 1.1 },
    7: { frequency: 5000, gain: 2.8, q: 1.0 },
  }, -0.6),

  P("rumble-cut", "Rumble Cut", "Utility", "18–30 Hz high-pass for live and vinyl.", {
    0: { frequency: 28, q: 0.8, enabled: true },
  }),
  P("hpf-80", "High-Pass 80", "Utility", "Standard vocal/guitar rumble filter.", {
    0: { frequency: 80, q: 0.71, enabled: true },
  }),
  P("hpf-120", "High-Pass 120", "Utility", "Aggressive low cut for dense arrangements.", {
    0: { frequency: 120, q: 0.75, enabled: true },
  }),
  P("air-only", "Air Only", "Utility", "Nothing but a 12 kHz shelf.", {
    8: { frequency: 12000, gain: 3.5, q: 0.7 },
  }, -0.5),
  P("notch-60", "Notch 60 Hz", "Utility", "Mains hum surgical cut.", {
    2: { type: "notch", frequency: 60, gain: 0, q: 8.0, enabled: true },
  }),
  P("notch-50", "Notch 50 Hz", "Utility", "EU mains hum surgical cut.", {
    2: { type: "notch", frequency: 50, gain: 0, q: 8.0, enabled: true },
  }),
  P("de-box", "De-Box", "Utility", "Broad 300–500 Hz cleanup.", {
    3: { frequency: 320, gain: -4.5, q: 1.6 },
    4: { frequency: 500, gain: -2.0, q: 1.3 },
  }, 0.8),
  P("de-harsh", "De-Harsh", "Utility", "Tame 2.5–6 kHz grit.", {
    6: { frequency: 2800, gain: -2.8, q: 1.8 },
    7: { frequency: 5500, gain: -3.4, q: 1.6 },
  }, 0.6),
  P("add-weight", "Add Weight", "Utility", "Low shelf at 110 Hz.", {
    1: { frequency: 110, gain: 3.2, q: 0.8 },
  }, -0.8),
  P("add-bite", "Add Bite", "Utility", "Narrow 4 kHz peak for attack.", {
    7: { frequency: 4000, gain: 3.8, q: 1.6 },
  }, -0.5),
  P("silk-highs", "Silk Highs", "Utility", "Broad expensive-sounding shelf from 8 kHz.", {
    8: { frequency: 8000, gain: 2.8, q: 0.65 },
  }, -0.4),
  P("vintage-70s", "Vintage 70s", "Utility", "Smoky: boosted 200 Hz, rolled 10 kHz.", {
    2: { frequency: 200, gain: 2.6, q: 0.9 },
    8: { frequency: 8000, gain: -3.0, q: 0.7 },
    9: { frequency: 14000, enabled: true },
  }),
  P("modern-bright", "Modern Bright", "Utility", "HPF, 3 kHz and 12 kHz lift.", {
    0: { frequency: 40, enabled: true },
    6: { frequency: 3000, gain: 1.8, q: 1.2 },
    8: { frequency: 12000, gain: 3.0, q: 0.7 },
  }, -0.6),
  P("low-pass-dull", "Low-Pass Dull", "Utility", "6.5 kHz ceiling for distance or lo-fi.", {
    9: { frequency: 6500, q: 0.71, enabled: true },
  }),
];

export function findPreset(id) {
  return PRESETS.find((p) => p.id === id) || PRESETS[0];
}

export function clonePresetBands(preset) {
  return cloneBands(preset.bands);
}
