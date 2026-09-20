// Owned by vertex-order/platforms — edit here. Vendored elsewhere via
// sync.toml; don't edit the copy there.
//
// Platform icon entries — how each platform renders in a Vertex Order
// listing row, consumed by the row icons and the standalone Platforms page.
// Sizes/styles here are PAGE size (1x, as PlatformIcon.dc.html renders them);
// the Zoomed grid shows the same entries at 2x via CSS zoom.
//
// `key` is the stable id a series-*.js entry's platformGroups reference
// (derived from the iconImg filename stem — kit's page.dc.html looks it up
// here and merges this record under the entry's own fields, so an entry
// never repeats the icon path/size/style, which live here exactly once).
// `name` here is a catalog label — every variant that platform has ever
// meant (e.g. Xbox One's "Physical; Digital; Enhanced; ...") — not a
// default: an entry always states its own `name` describing what that
// specific release actually supports, never inheriting this one.
//
// imgStyle carries sizing only (width/height). The light/dark tint filter is
// owned by PlatformIcon.dc.html (the .dc-plat-img rule) and applied to every
// icon automatically, so the source SVG's own fill colour is irrelevant. Put
// a `filter:` in imgStyle only to opt an icon out of the standard tint (e.g.
// nintendo-snes uses grayscale to keep its multi-colour logo legible).
//
// Classic script (not a module) so it loads via a plain <script src>.
// schema: platform-icons.schema.json
window.PLATFORM_ICONS = [
    { key: 'windows', iconImg: 'images/platforms/windows.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Windows (PC; Handheld; Digital)' },
    { key: 'macos', iconImg: 'images/platforms/macos.svg', iconSize: 16.5, imgStyle: 'width: auto; height: 16.5px;', name: 'macOS' },
    { key: 'linux', iconImg: 'images/platforms/linux.svg', iconSize: 20, imgStyle: 'width: auto; height: 20px;', name: 'Linux' },
    { key: 'gog', iconImg: 'images/platforms/gog.svg', iconSize: 16.75, imgStyle: 'width: auto; height: 16.75px;', name: 'GOG (PC)' },
    { key: 'steam', iconImg: 'images/platforms/steam.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Steam (PC; Handheld)' },
    { key: 'epic-games', iconImg: 'images/platforms/epic-games.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Epic Games Store (PC)' },
    { key: 'xbox-xs', iconImg: 'images/platforms/xbox-xs.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox Series X/S (Physical; Digital; Optimized; FPS Boost; 360 Compatibility; One Compatibility)' },
    { key: 'xbox-one', iconImg: 'images/platforms/xbox-one.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox One (Physical; Digital; Enhanced; Xbox One X Enhanced; 360 Compatibility)' },
    { key: 'xbox-360', iconImg: 'images/platforms/xbox-360.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox 360 (Physical; Xbox Live Arcade)' },
    { key: 'xbox-cloud', iconImg: 'images/platforms/xbox-cloud.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox Cloud Gaming' },
    { key: 'playstation-vr2', iconImg: 'images/platforms/playstation-vr2.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation VR2 (PS5)' },
    { key: 'playstation5', iconImg: 'images/platforms/playstation5.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation 5 (Physical; Digital; PS4 Compatibility; Pro Enhanced)' },
    { key: 'playstation-vr', iconImg: 'images/platforms/playstation-vr.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation VR (PS4; PS5 Compatibility)' },
    { key: 'playstation4', iconImg: 'images/platforms/playstation4.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation 4 (Physical; Digital)' },
    { key: 'playstation3', iconImg: 'images/platforms/playstation3.svg', iconSize: 8.06, imgStyle: 'width: auto; height: 8.06px;', name: 'PlayStation 3 (Physical; Digital; PSone Compatibility; PS2 Compatibility)' },
    { key: 'playstation2', iconImg: 'images/platforms/playstation2.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation 2 (Physical; PSone Compatibility)' },
    { key: 'playstation-classic', iconImg: 'images/platforms/playstation-classic.svg', iconSize: 8.48, imgStyle: 'width: auto; height: 8.48px;', name: 'PlayStation Classic' },
    { key: 'playstation1', iconImg: 'images/platforms/playstation1.svg', iconSize: 9, imgStyle: 'width: auto; height: 9px;', name: 'PlayStation (PSone) (Physical)' },
    { key: 'playstation-vita', iconImg: 'images/platforms/playstation-vita.svg', iconSize: 8.49, imgStyle: 'width: auto; height: 8.49px;', name: 'PlayStation Vita (Physical; Digital)' },
    { key: 'playstation-portable', iconImg: 'images/platforms/playstation-portable.svg', iconSize: 8.24, imgStyle: 'width: auto; height: 8.24px;', name: 'PlayStation Portable (PSP) (Physical; Digital; Universal Media Disk)' },
    { key: 'playstation-plus', iconImg: 'images/platforms/playstation-plus.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'PlayStation Plus (PS Plus)' },
    { key: 'nintendo-switch-2', iconImg: 'images/platforms/nintendo-switch-2.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Nintendo Switch 2 (Physical; Digital)' },
    { key: 'nintendo-switch', iconImg: 'images/platforms/nintendo-switch.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Nintendo Switch (Physical; Digital)' },
    { key: 'nintendo-wii-u', iconImg: 'images/platforms/nintendo-wii-u.svg', iconSize: 10.99, imgStyle: 'width: auto; height: 10.99px;', name: 'Nintendo Wii U (Physical; Virtual Console; WiiWare)' },
    { key: 'nintendo-wii', iconImg: 'images/platforms/nintendo-wii.svg', iconSize: 10.99, imgStyle: 'width: auto; height: 10.99px;', name: 'Nintendo Wii (Physical; Virtual Console; WiiWare)' },
    { key: 'nintendo-gamecube', iconImg: 'images/platforms/nintendo-gamecube.svg', iconSize: 18.5, imgStyle: 'width: auto; height: 18.5px;', name: 'Nintendo GameCube (Physical)' },
    { key: 'nintendo-snes-classic-edition', iconImg: 'images/platforms/nintendo-snes-classic-edition.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Super Nintendo Entertainment System (SNES) Classic Edition' },
    { key: 'nintendo-snes', iconImg: 'images/platforms/nintendo-snes.svg', iconSize: 14.25, imgStyle: 'width: auto; height: 14.25px; filter: grayscale(100%);', name: 'Super Nintendo Entertainment System (SNES) (Physical)' },
    { key: 'nintendo-nes-classic-edition', iconImg: 'images/platforms/nintendo-nes-classic-edition.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Nintendo NES Classic Edition' },
    { key: 'nintendo-nes-fc', iconImg: 'images/platforms/nintendo-nes-fc.svg', iconSize: 9.25, imgStyle: 'width: auto; height: 9.25px;', name: 'Nintendo Entertainment System (NES / FC) (Physical)' },
    { key: 'nintendo-nes', iconImg: 'images/platforms/nintendo-nes.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Nintendo Entertainment System (Physical)' },
    { key: 'nintendo-fc', iconImg: 'images/platforms/nintendo-fc.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Nintendo Famicom (Physical; Japan Only)', jpTag: true },
    { key: 'nintendo-3ds', iconImg: 'images/platforms/nintendo-3ds.svg', iconSize: 10.4, imgStyle: 'width: auto; height: 10.4px;', name: 'Nintendo 3DS (Physical; Digital)' },
    { key: 'nintendo-ds', iconImg: 'images/platforms/nintendo-ds.svg', iconSize: 10.4, imgStyle: 'width: auto; height: 10.4px;', name: 'Nintendo DS (Physical; DSi Digital)' },
    { key: 'nintendo-game-boy-advance', iconImg: 'images/platforms/nintendo-game-boy-advance.svg', iconSize: 12.5, imgStyle: 'width: auto; height: 12.5px;', name: 'Game Boy Advance (Physical)' },
    { key: 'nintendo-game-boy', iconImg: 'images/platforms/nintendo-game-boy.svg', iconSize: 12.5, imgStyle: 'width: auto; height: 12.5px;', name: 'Nintendo Game Boy (Physical)' },
    { key: 'ouya', iconImg: 'images/platforms/ouya.svg', iconSize: 13.5, imgStyle: 'width: auto; height: 13.5px;', name: 'Ouya' },
    { key: 'arcade', iconImg: 'images/platforms/arcade.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Arcade' },
    { key: 'wonderswan', iconImg: 'images/platforms/wonderswan.svg', iconSize: 15.93, imgStyle: 'width: auto; height: 15.93px;', name: 'WonderSwan Color (Physical; Japan Only)', jpTag: true },
    { key: 'msx2', iconImg: 'images/platforms/msx2.svg', iconSize: 12.93, imgStyle: 'width: auto; height: 12.93px;', name: 'MSX2 (Physical; Japan Only)', jpTag: true },
    { key: 'msx', iconImg: 'images/platforms/msx.svg', iconSize: 12.73, imgStyle: 'width: auto; height: 12.73px;', name: 'MSX (Physical; Japan Only)', jpTag: true },
    { key: 'sharp-x1', iconImg: 'images/platforms/sharp-x1.svg', iconSize: 10.25, imgStyle: 'width: auto; height: 10.25px;', name: 'Sharp X1 (Physical; Japan Only)', jpTag: true },
    { key: 'pc8801', iconImg: 'images/platforms/pc8801.svg', iconSize: 8.875, imgStyle: 'width: auto; height: 8.875px;', suffix: 'mkII SR', suffixFontSize: '9.75px', suffixOffsetY: 1, name: 'NEC PC-8801mkII SR (Physical; Japan Only)', jpTag: true },
    { key: 'globe', iconImg: 'images/platforms/globe.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Browser' },
    { key: 'android2', iconImg: 'images/platforms/android2.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Android' },
    { key: 'apple', iconImg: 'images/platforms/apple.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'iOS' },
    { key: 'apple-arcade', iconImg: 'images/platforms/apple-arcade.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Apple Arcade' },
    { key: 'amazon', iconImg: 'images/platforms/amazon.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Amazon App Store' },
    { key: 'facebook', iconImg: 'images/platforms/facebook.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Facebook (Messenger)' },
    { key: 'windows-phone', iconImg: 'images/platforms/windows-phone.svg', iconSize: 17.25, imgStyle: 'width: auto; height: 17.25px;', name: 'Windows Phone' },
    { key: 'mobile-phone', iconImg: 'images/platforms/mobile-phone.svg', iconSize: 16.75, imgStyle: 'width: auto; height: 16.75px;', name: 'Mobile Phones' },
    { key: 'blu-ray-ultra-hd', iconImg: 'images/platforms/blu-ray-ultra-hd.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'UltraHD Blu-ray' },
    { key: 'blu-ray', iconImg: 'images/platforms/blu-ray.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'Blu-ray' },
    { key: 'cast', iconImg: 'images/platforms/cast.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Digital Streaming' },
    { key: 'dvd', iconImg: 'images/platforms/dvd.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'DVD' },
    { key: 'laserdisc', iconImg: 'images/platforms/laserdisc.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'LaserDisc' },
    { key: 'compact-disc', iconImg: 'images/platforms/compact-disc.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'Compact Disc (CD)' },
    { key: 'vhs', iconImg: 'images/platforms/vhs.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'VHS Tapes' },
    { key: 'book', iconImg: 'images/platforms/book.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Book' },
    { key: 'youtube', iconImg: 'images/platforms/youtube.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Youtube' },
    { key: 'fan-translation', iconImg: 'images/platforms/fan-translation.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan Translation' },
    { key: 'fan-movie', iconImg: 'images/platforms/fan-movie.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan game movie video' },
    { key: 'fan-audiobook', iconImg: 'images/platforms/fan-audiobook.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan Audiobook' },
    { key: 'fan-recap', iconImg: 'images/platforms/fan-recap.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan story recap video' },
    { key: 'fan-playthrough', iconImg: 'images/platforms/fan-playthrough.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan playthrough video' },
];
