// 계약 2 열거형 — 서버 값(snake_case)과 한국어 라벨을 클라이언트가 소유한다 (docs/api/app-api-v1.md 2절).
import 'package:json_annotation/json_annotation.dart';

/// 서버가 계약에 없는 열거형 값을 보냈을 때 받는 `unknown` 의 라벨 (계약 7).
const String unknownLabel = '알 수 없음';

/// 알림 전달 강도 (배지).
@JsonEnum(valueField: 'value')
enum DeliveryMode {
  instant('instant', '즉시'),
  quiet('quiet', '조용히'),
  feedOnly('feed_only', '피드만'),
  experiment('experiment', '실험'),
  unknown('unknown', unknownLabel);

  const DeliveryMode(this.value, this.label);
  final String value;
  final String label;
}

/// 사용자 판정. Flutter `Feedback` 과 겹치지 않게 이름을 붙인다.
@JsonEnum(valueField: 'value')
enum FeedbackVerdict {
  useful('useful', '유용'),
  notUseful('not_useful', '불필요'),
  unknown('unknown', unknownLabel);

  const FeedbackVerdict(this.value, this.label);
  final String value;
  final String label;
}

/// 피드 칩.
@JsonEnum(valueField: 'value')
enum FeedFilter {
  all('all', '전체'),
  instant('instant', '즉시'),
  quiet('quiet', '조용히'),
  experiment('experiment', '실험'),
  useful('useful', '👍 유용');

  const FeedFilter(this.value, this.label);
  final String value;
  final String label;
}

/// 변화 종류 (백엔드 `Kind`).
@JsonEnum(valueField: 'value')
enum Kind {
  releaseMajor('release_major', '메이저 릴리즈'),
  releasePatch('release_patch', '패치 릴리즈'),
  technique('technique', '기법·논문'),
  survey('survey', '서베이·전망'),
  news('news', '뉴스·사건'),
  tutorial('tutorial', '튜토리얼'),
  promo('promo', '홍보·구인'),
  other('other', '기타'),
  unknown('unknown', unknownLabel);

  const Kind(this.value, this.label);
  final String value;
  final String label;
}

/// 걸러진 관문. 선언 순서가 GateBar 구간 순서다 (`stale` 여섯째, `cluster_dup` 일곱째).
@JsonEnum(valueField: 'value')
enum Gate {
  exclude('exclude', 'exclude'),
  dedup('dedup', '중복'),
  screening('screening', '선별'),
  score('score', '점수'),
  judgment('judgment', '판정'),
  stale('stale', '오래됨'),
  clusterDup('cluster_dup', '클러스터 하루 1건'),
  unknown('unknown', unknownLabel);

  const Gate(this.value, this.label);
  final String value;

  /// GateBar 범례 라벨.
  final String label;

  /// 탈락 태그 라벨. `cluster_dup` 은 탈락이 아니라 억제라, `unknown` 은 뜻을 몰라 `탈락` 을 붙이지 않는다.
  String get tagLabel =>
      this == clusterDup || this == unknown ? label : '$label 탈락';
}

/// 07 "이 알림이 온 이유" 우측 라벨.
@JsonEnum(valueField: 'value')
enum Routing {
  passed('passed', '통과'),
  exploreSlot('explore_slot', '경계 → 탐색 슬롯'),
  restored('restored', '직접 복원'),
  dropped('dropped', '탈락'),
  clusterDup('cluster_dup', '같은 이슈 → 앞 알림에 병기'),
  unknown('unknown', unknownLabel);

  const Routing(this.value, this.label);
  final String value;
  final String label;
}

@JsonEnum(valueField: 'value')
enum SourceType {
  rss('rss', 'RSS'),
  githubRelease('github_release', 'GitHub 릴리즈'),
  youtube('youtube', 'YouTube'),
  hackernews('hackernews', 'Hacker News'),
  hfPapers('hf_papers', 'HF Papers'),
  unknown('unknown', unknownLabel);

  const SourceType(this.value, this.label);
  final String value;
  final String label;
}

@JsonEnum(valueField: 'value')
enum SourceGroup {
  blogRss('blog_rss', '기술 블로그 · RSS'),
  paperReleaseVideo('paper_release_video', '논문 · 릴리즈 · 영상'),
  community('community', '커뮤니티'),
  unknown('unknown', unknownLabel);

  const SourceGroup(this.value, this.label);
  final String value;
  final String label;
}

@JsonEnum(valueField: 'value')
enum ImportanceBand {
  high('high', 'importance 5 · 4'),
  mid('mid', 'importance 3'),
  low('low', 'importance 2 · 1');

  const ImportanceBand(this.value, this.label);
  final String value;
  final String label;
}

/// 05 중요도별 강도 세그먼트.
@JsonEnum(valueField: 'value')
enum DeliveryChoice {
  instant('instant', '즉시'),
  quiet('quiet', '조용히'),
  feedOnly('feed_only', '피드만'),
  unknown('unknown', unknownLabel);

  const DeliveryChoice(this.value, this.label);
  final String value;
  final String label;
}

@JsonEnum(valueField: 'value')
enum NotifyChannel {
  fcm('fcm', '앱 푸시 (FCM)'),
  discord('discord', 'Discord 채널'),
  telegram('telegram', 'Telegram 봇');

  const NotifyChannel(this.value, this.label);
  final String value;
  final String label;
}

/// 09·10 세그먼트.
@JsonEnum(valueField: 'value')
enum FilteredView {
  source('source', '소스별'),
  kind('kind', '종류별'),
  gate('gate', '관문별');

  const FilteredView(this.value, this.label);
  final String value;
  final String label;
}

@JsonEnum(valueField: 'value')
enum GroupSort {
  countDesc('count_desc', '많은 순'),
  nameAsc('name_asc', '이름순');

  const GroupSort(this.value, this.label);
  final String value;
  final String label;
}

@JsonEnum(valueField: 'value')
enum SavedSort {
  savedDesc('saved_desc', '최근 찜한 순'),
  savedAsc('saved_asc', '오래된 순'),
  deliveredDesc('delivered_desc', '알림 시간 순');

  const SavedSort(this.value, this.label);
  final String value;
  final String label;
}

/// FCM 기기 플랫폼 (`POST /devices`).
@JsonEnum(valueField: 'value')
enum DevicePlatform {
  android('android'),
  ios('ios'),
  unknown('unknown');

  const DevicePlatform(this.value);
  final String value;
}
