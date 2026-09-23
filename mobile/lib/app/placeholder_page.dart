// 자리표시 화면 — 화면 번호·제목과 하위 화면 링크만 둔다. 각 화면 작업(F2~)이 교체한다.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_text.dart';
import '../core/widgets/widgets.dart';

class PlaceholderLink {
  const PlaceholderLink(this.label, this.location, {this.push = false});

  final String label;
  final String location;

  /// true 면 `push` (루트 네비게이터의 07), 아니면 `go` (같은 탭의 하위 경로).
  final bool push;
}

class PlaceholderPage extends StatelessWidget {
  const PlaceholderPage({
    super.key,
    required this.screen,
    required this.title,
    this.isRoot = false,
    this.note,
    this.links = const [],
  });

  /// 디자인 화면 번호 (`03`) 또는 `–` (디자인 없음).
  final String screen;
  final String title;
  final bool isRoot;
  final String? note;
  final List<PlaceholderLink> links;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: isRoot ? RootTopBar(title: title) : SubTopBar(title: title),
      body: ListView(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
            child: Text(
              ['화면 $screen · 준비 중', ?note].join('\n'),
              style: AppText.captionMd,
            ),
          ),
          if (links.isNotEmpty) ...[
            const SectionLabel('이동'),
            AppCard(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              gap: 0,
              children: [
                for (final (index, link) in links.indexed)
                  ValueRow(
                    title: link.label,
                    value: '',
                    isLast: index == links.length - 1,
                    onTap: () => link.push
                        ? context.push(link.location)
                        : context.go(link.location),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
