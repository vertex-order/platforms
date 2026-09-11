// Owned by vertex-order/platforms — edit here. Vendored elsewhere via
// sync.toml; don't edit the copy there.
//
// Platform icon entries — how each platform renders in a Vertex Order
// listing row, consumed by the row icons and the standalone Platforms page.
// Sizes/styles here are PAGE size (1x, as PlatformIcon.dc.html renders them);
// the Zoomed grid shows the same entries at 2x via CSS zoom.
//
// imgStyle carries sizing only (width/height). The light/dark tint filter is
// owned by PlatformIcon.dc.html (the .dc-plat-img rule) and applied to every
// icon automatically, so the source SVG's own fill colour is irrelevant. Put
// a `filter:` in imgStyle only to opt an icon out of the standard tint (e.g.
// nintendo-snes uses grayscale to keep its multi-colour logo legible).
//
// Classic script (not a module) so it loads via a plain <script src>.
window.PLATFORM_ICONS = [
    { iconImg: 'images/platforms/windows.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Windows (PC; Handheld; Digital)' },
    { iconImg: 'images/platforms/macos.svg', iconSize: 16.5, imgStyle: 'width: auto; height: 16.5px;', name: 'macOS' },
    { iconImg: 'images/platforms/linux.svg', iconSize: 20, imgStyle: 'width: auto; height: 20px;', name: 'Linux' },
    { iconImg: 'images/platforms/gog.svg', iconSize: 16.75, imgStyle: 'width: auto; height: 16.75px;', name: 'GOG (PC)' },
    { iconImg: 'images/platforms/steam.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Steam (PC; Handheld)' },
    { iconImg: 'images/platforms/epic-games.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Epic Games Store (PC)' },
    { iconImg: 'images/platforms/xbox-xs.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox Series X/S (Physical; Digital; Optimized; FPS Boost; 360 Compatibility; One Compatibility)' },
    { iconImg: 'images/platforms/xbox-one.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox One (Physical; Digital; Enhanced; Xbox One X Enhanced; 360 Compatibility)' },
    { iconImg: 'images/platforms/xbox-360.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox 360 (Physical; Xbox Live Arcade)' },
    { iconImg: 'images/platforms/xbox-cloud.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Xbox Cloud Gaming' },
    { iconImg: 'images/platforms/playstation-vr2.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation VR2 (PS5)' },
    { iconImg: 'images/platforms/playstation5.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation 5 (Physical; Digital; PS4 Compatibility; Pro Enhanced)' },
    { iconImg: 'images/platforms/playstation-vr.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation VR (PS4; PS5 Compatibility)' },
    { iconImg: 'images/platforms/playstation4.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation 4 (Physical; Digital)' },
    { iconImg: 'images/platforms/playstation3.svg', iconSize: 8.06, imgStyle: 'width: auto; height: 8.06px;', name: 'PlayStation 3 (Physical; Digital; PSone Compatibility; PS2 Compatibility)' },
    { iconImg: 'images/platforms/playstation2.svg', iconSize: 8.05, imgStyle: 'width: auto; height: 8.05px;', name: 'PlayStation 2 (Physical; PSone Compatibility)' },
    { iconImg: 'images/platforms/playstation-classic.svg', iconSize: 8.48, imgStyle: 'width: auto; height: 8.48px;', name: 'PlayStation Classic' },
    { iconImg: 'images/platforms/playstation1.svg', iconSize: 9, imgStyle: 'width: auto; height: 9px;', name: 'PlayStation (PSone) (Physical)' },
    { iconImg: 'images/platforms/playstation-vita.svg', iconSize: 8.49, imgStyle: 'width: auto; height: 8.49px;', name: 'PlayStation Vita (Physical; Digital)' },
    { iconImg: 'images/platforms/playstation-portable.svg', iconSize: 8.24, imgStyle: 'width: auto; height: 8.24px;', name: 'PlayStation Portable (PSP) (Physical; Digital; Universal Media Disk)' },
    { iconImg: 'images/platforms/playstation-plus.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'PlayStation Plus (PS Plus)' },
    { iconImg: 'images/platforms/nintendo-switch-2.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Nintendo Switch 2 (Physical; Digital)' },
    { iconImg: 'images/platforms/nintendo-switch.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Nintendo Switch (Physical; Digital)' },
    { iconImg: 'images/platforms/nintendo-wii-u.svg', iconSize: 10.99, imgStyle: 'width: auto; height: 10.99px;', name: 'Nintendo Wii U (Physical; Virtual Console; WiiWare)' },
    { iconImg: 'images/platforms/nintendo-wii.svg', iconSize: 10.99, imgStyle: 'width: auto; height: 10.99px;', name: 'Nintendo Wii (Physical; Virtual Console; WiiWare)' },
    { iconImg: 'images/platforms/nintendo-gamecube.svg', iconSize: 18.5, imgStyle: 'width: auto; height: 18.5px;', name: 'Nintendo GameCube (Physical)' },
    { iconImg: 'images/platforms/nintendo-snes-classic-edition.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Super Nintendo Entertainment System (SNES) Classic Edition' },
    { iconImg: 'images/platforms/nintendo-snes.svg', iconSize: 14.25, imgStyle: 'width: auto; height: 14.25px; filter: grayscale(100%);', name: 'Super Nintendo Entertainment System (SNES) (Physical)' },
    { iconImg: 'images/platforms/nintendo-nes-classic-edition.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Nintendo NES Classic Edition' },
    { iconImg: 'images/platforms/nintendo-nes-fc.svg', iconSize: 9.25, imgStyle: 'width: auto; height: 9.25px;', name: 'Nintendo Entertainment System (NES / FC) (Physical)' },
    { iconImg: 'images/platforms/nintendo-nes.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Nintendo Entertainment System (Physical)' },
    { iconImg: 'images/platforms/nintendo-fc.svg', iconSize: 9.61, imgStyle: 'width: auto; height: 9.61px;', name: 'Nintendo Famicom (Physical; Japan Only)', jpTag: true },
    { iconImg: 'images/platforms/nintendo-3ds.svg', iconSize: 10.4, imgStyle: 'width: auto; height: 10.4px;', name: 'Nintendo 3DS (Physical; Digital)' },
    { iconImg: 'images/platforms/nintendo-ds.svg', iconSize: 10.4, imgStyle: 'width: auto; height: 10.4px;', name: 'Nintendo DS (Physical; DSi Digital)' },
    { iconImg: 'images/platforms/nintendo-game-boy-advance.svg', iconSize: 12.5, imgStyle: 'width: auto; height: 12.5px;', name: 'Game Boy Advance (Physical)' },
    { iconImg: 'images/platforms/nintendo-game-boy.svg', iconSize: 12.5, imgStyle: 'width: auto; height: 12.5px;', name: 'Nintendo Game Boy (Physical)' },
    { iconImg: 'images/platforms/ouya.svg', iconSize: 13.5, imgStyle: 'width: auto; height: 13.5px;', name: 'Ouya' },
    { iconImg: 'images/platforms/arcade.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Arcade' },
    { iconImg: 'images/platforms/wonderswan.svg', iconSize: 15.93, imgStyle: 'width: auto; height: 15.93px;', name: 'WonderSwan Color (Physical; Japan Only)', jpTag: true },
    { iconImg: 'images/platforms/msx2.svg', iconSize: 12.93, imgStyle: 'width: auto; height: 12.93px;', name: 'MSX2 (Physical; Japan Only)', jpTag: true },
    { iconImg: 'images/platforms/msx.svg', iconSize: 12.73, imgStyle: 'width: auto; height: 12.73px;', name: 'MSX (Physical; Japan Only)', jpTag: true },
    { iconImg: 'images/platforms/sharp-x1.svg', iconSize: 10.25, imgStyle: 'width: auto; height: 10.25px;', name: 'Sharp X1 (Physical; Japan Only)', jpTag: true },
    { iconImg: 'images/platforms/pc8801.svg', iconSize: 8.875, imgStyle: 'width: auto; height: 8.875px;', suffix: 'mkII SR', suffixFontSize: '9.75px', suffixOffsetY: 1, name: 'NEC PC-8801mkII SR (Physical; Japan Only)', jpTag: true },
    { iconImg: 'images/platforms/globe.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Browser' },
    { iconImg: 'images/platforms/android2.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Android' },
    { iconImg: 'images/platforms/apple.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'iOS' },
    { iconImg: 'images/platforms/apple-arcade.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Apple Arcade' },
    { iconImg: 'images/platforms/amazon.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Amazon App Store' },
    { iconImg: 'images/platforms/facebook.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Facebook (Messenger)' },
    { iconImg: 'images/platforms/windows-phone.svg', iconSize: 17.25, imgStyle: 'width: auto; height: 17.25px;', name: 'Windows Phone' },
    { iconImg: 'images/platforms/mobile-phone.svg', iconSize: 16.75, imgStyle: 'width: auto; height: 16.75px;', name: 'Mobile Phones' },
    { iconImg: 'images/platforms/blu-ray-ultra-hd.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'UltraHD Blu-ray' },
    { iconImg: 'images/platforms/blu-ray.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'Blu-ray' },
    { iconImg: 'images/platforms/cast.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Digital Streaming' },
    { iconImg: 'images/platforms/dvd.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'DVD' },
    { iconImg: 'images/platforms/laserdisc.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'LaserDisc' },
    { iconImg: 'images/platforms/compact-disc.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'Compact Disc (CD)' },
    { iconImg: 'images/platforms/vhs.svg', iconSize: 10.14, imgStyle: 'width: auto; height: 10.14px;', name: 'VHS Tapes' },
    { iconImg: 'images/platforms/book.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Book' },
    { iconImg: 'images/platforms/youtube.svg', iconSize: 16, imgStyle: 'width: auto; height: 16px;', name: 'Youtube' },
    { iconImg: 'images/platforms/fan-translation.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan Translation' },
    { iconImg: 'images/platforms/fan-movie.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan game movie video' },
    { iconImg: 'images/platforms/fan-audiobook.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan Audiobook' },
    { iconImg: 'images/platforms/fan-recap.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan story recap video' },
    { iconImg: 'images/platforms/fan-playthrough.svg', iconSize: 22, imgStyle: 'width: auto; height: 22px;', name: 'Fan playthrough video' },
];
