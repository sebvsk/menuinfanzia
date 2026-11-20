// The invented draft recipes were removed on 20/11/2026: every recipe now comes from the recipe book of
// Roma Capitale (recipes_comune.js, built by scripts/build_cene.py). This array is filled in index.html.
const RECIPES = [];

// Seasonal vegetables and fruit in Lazio, by month (draft, general knowledge).
const SEASON = {
  1: [["cavolfiore", "broccoli", "finocchi", "carciofi", "spinaci"], ["arance", "mandarini", "mele", "pere", "kiwi"]],
  2: [["cavolfiore", "broccoli", "finocchi", "carciofi", "spinaci"], ["arance", "mandarini", "mele", "pere", "kiwi"]],
  3: [["carciofi", "spinaci", "finocchi", "bieta", "lattuga"], ["arance", "mele", "pere", "kiwi"]],
  4: [["asparagi", "carciofi", "spinaci", "lattuga", "bieta"], ["fragole", "mele", "arance"]],
  5: [["zucchine", "asparagi", "fagiolini", "lattuga", "carote"], ["fragole", "ciliegie", "nespole"]],
  6: [["zucchine", "fagiolini", "pomodori", "melanzane", "peperoni"], ["albicocche", "ciliegie", "pesche", "melone"]],
  7: [["zucchine", "pomodori", "melanzane", "peperoni", "fagiolini"], ["pesche", "albicocche", "anguria", "melone"]],
  8: [["zucchine", "pomodori", "melanzane", "peperoni", "cetrioli"], ["pesche", "fichi", "anguria", "susine"]],
  9: [["zucchine", "peperoni", "melanzane", "pomodori", "zucca"], ["uva", "fichi", "pere", "mele"]],
  10: [["zucca", "broccoli", "cavolfiore", "spinaci", "bieta"], ["uva", "mele", "pere", "cachi"]],
  11: [["zucca", "broccoli", "cavolfiore", "finocchi", "spinaci"], ["mele", "pere", "cachi", "mandarini", "kiwi"]],
  12: [["broccoli", "cavolfiore", "finocchi", "carciofi", "spinaci"], ["mandarini", "arance", "mele", "pere", "kiwi"]],
};
