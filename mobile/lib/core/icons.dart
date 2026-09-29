// 디자인 아이콘 26종 — gen.py.txt icon() 의 SVG 경로를 공통 래퍼로 그리는 AppIcon.
import 'package:flutter/widgets.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// 이름 → SVG 본문 (viewBox 0 0 24 24). docs/design/tokens.md 아이콘 표와 같다.
const Map<String, String> appIconPaths = {
  'back': '<path d="M15 5l-7 7 7 7"/>',
  'bell': '<path d="M6 8a6 6 0 0 1 12 0v5l2 3H4l2-3z"/><path d="M10 19a2 2 0 0 0 4 0"/>',
  'home': '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
  'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  'sliders': '<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  'thumbup': '<path d="M7 11v9H3v-9zM7 11l4-8a2 2 0 0 1 2 2v4h5a2 2 0 0 1 2 2l-1 7a2 2 0 0 1-2 2H7"/>',
  'thumbdown': '<path d="M17 13V4h4v9zM17 13l-4 8a2 2 0 0 1-2-2v-4H6a2 2 0 0 1-2-2l1-7a2 2 0 0 1 2-2h10"/>',
  'external': '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v6H4V6h6"/>',
  'chev': '<path d="M9 5l7 7-7 7"/>',
  'chevd': '<path d="M5 9l7 7 7-7"/>',
  'plus': '<path d="M12 5v14M5 12h14"/>',
  'flask': '<path d="M9 3h6M10 3v6L4 20h16l-6-11V3"/>',
  'check': '<path d="M5 12l5 5 9-10"/>',
  'search': '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  'github': '<path d="M12 2a10 10 0 0 0-3 19.5c.5 0 .7-.2.7-.5v-2c-2.8.6-3.4-1.2-3.4-1.2-.4-1.1-1-1.4-1-1.4-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.3 1.1 2.9.8.1-.6.3-1.1.6-1.3-2.2-.3-4.6-1.1-4.6-5a4 4 0 0 1 1-2.7 3.7 3.7 0 0 1 .1-2.7s.8-.3 2.8 1a9.5 9.5 0 0 1 5 0c1.9-1.3 2.8-1 2.8-1 .5 1.4.2 2.4.1 2.7a4 4 0 0 1 1 2.7c0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.8v2.7c0 .3.2.6.7.5A10 10 0 0 0 12 2z"/>',
  'discord': '<path d="M8 17c-2.5 0-4-1.5-5-3 0-3 1-6 2.5-8.5C7 5 8.5 4.5 10 4.5l.5 1.5a12 12 0 0 1 3 0l.5-1.5c1.5 0 3 .5 4.5 1 1.5 2.5 2.5 5.5 2.5 8.5-1 1.5-2.5 3-5 3l-1-1.5c-1.5.5-3.5.5-5 0z"/><circle cx="9.5" cy="12" r="1"/><circle cx="14.5" cy="12" r="1"/>',
  'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  'rss': '<path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1.5"/>',
  'youtube': '<rect x="3" y="6" width="18" height="12" rx="3"/><path d="M10 9l5 3-5 3z"/>',
  'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  'trend': '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  'logo': '<path d="M4 18L10 6l4 8 2-4 4 8"/>',
  'bookmark': '<path d="M6 3h12v18l-6-4-6 4z"/>',
  'bookmarkfill': '<path d="M6 3h12v18l-6-4-6 4z" fill="currentColor"/>',
  'folder': '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  'dots': '<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>',
};

/// 공통 래퍼로 감싼 SVG 문자열. 선 굵기는 표시 크기와 무관하게 viewBox 기준 1.8 이고,
/// `bookmarkfill` 의 `currentColor` 채움도 선 색과 같다.
String appIconSvg(String name, Color color) {
  final hex = (color.toARGB32() & 0xFFFFFF).toRadixString(16).padLeft(6, '0');
  final paths = (appIconPaths[name] ?? '').replaceAll('currentColor', '#$hex');
  return '<svg viewBox="0 0 24 24" fill="none" stroke="#$hex" '
      'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      '$paths</svg>';
}

class AppIcon extends StatelessWidget {
  const AppIcon(
    this.name, {
    super.key,
    this.size = 20,
    this.color = const Color(0xFF1C1B19),
  });

  final String name;
  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    assert(appIconPaths.containsKey(name), '알 수 없는 아이콘 이름 "$name".');
    return SvgPicture.string(
      appIconSvg(name, color),
      width: size,
      height: size,
    );
  }
}
