# Final image-generation prompts

The previews were produced with the built-in image generation tool in
`ui-mockup` mode. The following are the final prompts used.

## Public groups

> Create a high-fidelity desktop web UI mockup for the implemented “Blitz Fut” React + Material UI application. This is a UI mockup, 1440×1000 landscape browser viewport, not a marketing poster. Use only a restrained palette: off-white background #f7f8f4, near-black text #172019, football green #237a45, subtle grey borders, and normal semantic status colours only. Flat modern Material Design, system sans-serif, rounded 12px cards, generous whitespace, no gradients, no photos, no illustrations, no invented logos.
>
> Show the public competition page in English. Top app bar: “Blitz Fut” on the left and a small outlined “Admin” action on the right. Main heading: “Blitz Fut Cup”, a green-outlined status chip “Knockout”, subtext “2026 · 8 teams”. Under it show scrollable Material UI tabs exactly: “Groups”, “Matches”, “Knockout”, “Statistics”, “Teams”, with “Groups” active in green.
>
> Main content shows two side-by-side outlined standings cards titled “Group A” and “Group B”. Each contains a crisp table with columns “#”, “Team”, “P”, “W”, “D”, “L”, “GD”, “Pts”. Group A rows: 1 Shamrock FC — P3 W3 D0 L0 GD+6 Pts9; 2 Blackwater Athletic — P3 W2 D0 L1 GD+2 Pts6; 3 Green Street — P3 W1 D0 L2 GD−2 Pts3; 4 Northside Five — P3 W0 D0 L3 GD−6 Pts0. Group B rows: 1 Riverside Rovers 9 points; 2 The Harps 6; 3 Astro United 3; 4 Docklands FC 0. Give the top two qualifying rows in each group a very pale green background. Add a compact lower section titled “Latest matches” with two match cards: “Shamrock FC 3 — 1 Green Street” and “Riverside Rovers 2 — 0 The Harps”, each with a small “Final” chip.
>
> Make all text correctly spelled and legible. The design must look like an achievable screenshot of the described MUI implementation, with no mobile phone frame and no features beyond those listed.

## Mobile match entry

> Create a high-fidelity mobile web UI mockup for the implemented “Blitz Fut” React + Material UI application. This is a tall 430×1100 mobile browser viewport, not a marketing poster. Use only off-white #f7f8f4, near-black #172019, football green #237a45, subtle grey borders, and normal semantic status colours. Flat Material Design, system sans-serif, rounded 12px cards, no gradients, no photos, no illustrations, no invented logo.
>
> Show the administrator match-result entry page in English. Compact top app bar: “Blitz Fut” left and “Sign out” text button right. Main eyebrow in green: “Final”. Main heading exactly “Shamrock FC vs The Harps”. Helper text: “Distribute every normal-time goal before completing the match.”
>
> Show the first team card fully and the start of the second card below, demonstrating the vertical mobile layout. First card header: “Shamrock FC” left and a large score “2” right. Player rows: Liam Byrne, with a “Goals” counter showing minus button, 1, plus button; an “Assists” counter showing minus, 1, plus. Cian Murphy, Goals 1 and Assists 0. Eoin Kelly, Goals 0 and Assists 0. Each counter is a compact outlined Material UI button group. Add a divider and “Own goals received” counter at 0. Second card begins with “The Harps” and large score “2”; show Patrick Ryan with Goals 2 and Assists 1.
>
> Because the score is tied 2–2 in a knockout final, include an outlined panel titled “Winner after penalties” with radio choices “Shamrock FC” and “The Harps”, with neither selected. At the bottom show a plain “Cancel” button and prominent green “Complete match” button.
>
> Ensure exact spelling and legible UI text. Make it look like an achievable responsive screenshot of a React/MUI app. Do not add dates, times, penalty scores, player accounts, notifications, payment controls, native-app chrome, or unrelated features.

## Public knockout

> Create a high-fidelity desktop web UI mockup for the implemented “Blitz Fut” React + Material UI public competition page, focused on the knockout bracket. This is a 1440×900 landscape browser viewport and must look like a real application screenshot, not a poster. Palette: off-white #f7f8f4, near-black #172019, football green #237a45, subtle grey outlines; flat Material Design, system sans-serif, rounded 12px cards, no gradients, photos, illustrations, or invented logos.
>
> Top app bar: “Blitz Fut” left, outlined “Admin” action right. Main heading “Blitz Fut Cup” with outlined green “Knockout” chip, subtext “2026 · 8 teams”. Material tabs exactly “Groups”, “Matches”, “Knockout”, “Statistics”, “Teams”; make “Knockout” active with a green underline.
>
> Below, show a horizontally structured knockout bracket with two columns labeled “Semi-finals” and “Final”. In the Semi-finals column, two vertically separated match cards: 1. small “Final” chip, Shamrock FC 3, The Harps 2. 2. small “Final” chip, Riverside Rovers 1, Blackwater Athletic 1 (p), where “(p)” is next to Blackwater Athletic to indicate they qualified on penalties. In the Final column, centered between the semi-final cards, one pending match card: small “Pending” chip, Shamrock FC —, Blackwater Athletic —. Below the final card, a smaller pending “Third place” match card: The Harps —, Riverside Rovers —. Use em dashes for pending scores. Arrange cards with believable spacing and alignment like the implemented horizontally scrollable responsive bracket; do not draw elaborate tournament connector lines.
>
> At the lower edge, include two compact leaderboard preview cards side by side titled “Top scorers” and “Top assisters”, with a few legible example names: Liam Byrne, Hugo Costa, Adam Walsh. Make all text correctly spelled. Do not add dates or times, penalty scores, betting, payments, notifications, accounts, or unrelated features.
