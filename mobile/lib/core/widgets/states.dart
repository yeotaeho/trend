// 빈·로딩·오류 상태 — 디자인이 없어 토큰 색·글자만 쓴 가운데 정렬 안내.
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_text.dart';
import 'buttons.dart';

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return _Centered(
      children: [
        Text(message, textAlign: TextAlign.center, style: AppText.captionMd),
      ],
    );
  }
}

class LoadingState extends StatelessWidget {
  const LoadingState({super.key});

  @override
  Widget build(BuildContext context) {
    return const _Centered(
      children: [
        SizedBox.square(
          dimension: 24,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: AppColors.primary,
          ),
        ),
      ],
    );
  }
}

/// [message] 는 ApiException.message 를 그대로 보여 준다.
class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return _Centered(
      children: [
        Text(message, textAlign: TextAlign.center, style: AppText.captionNote),
        if (onRetry != null) AccentTextButton(label: '다시 시도', onTap: onRetry),
      ],
    );
  }
}

class _Centered extends StatelessWidget {
  const _Centered({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          spacing: 12,
          children: children,
        ),
      ),
    );
  }
}
