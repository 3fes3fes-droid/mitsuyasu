# Baccarat card faces

All 52 card faces are self-contained SVGs by Adrian Kennard (RevK),
released under CC0 1.0 Universal. They include illustrated J, Q and K cards.

Original artwork and license: https://www.me.uk/cards/
Retrieved from: https://github.com/letele/playing-cards/tree/865a78eb940c1232e4b21523577c8fca52f694fe/assets
Upstream commit: 865a78eb940c1232e4b21523577c8fca52f694fe
Retrieved: 2026-10-03
License text: LICENSE.txt

Files were renamed to `<suit>-<rank>.svg`. The ace of spades uses the original
spade symbol as a plain central pip, matching the other aces; its decorative
QR code and credit text were removed. Other artwork is unchanged.
The baccarat page loads these same-origin assets using suit and rank, without
external image services or runtime packages. CSS card backs are retained; squeeze reveal margins and corner masks are
adjusted to the SVG pip positions.
