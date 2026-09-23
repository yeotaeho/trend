// 11 찜 상태 — 폴더 칩·찜 목록·보기 조건을 들고, 쓰기는 낙관적으로 반영한 뒤 실패하면 되돌린다.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/labels.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repositories.dart';
import '../../data/repositories/repository_providers.dart';

/// 목록 조회 조건 — 폴더 칩·`안 읽음` 토글·정렬.
class SavedQuery {
  const SavedQuery({
    this.folderId,
    this.unreadOnly = false,
    this.sort = SavedSort.savedDesc,
  });

  /// `null` 이면 `전체`.
  final String? folderId;
  final bool unreadOnly;
  final SavedSort sort;

  /// 쓰기 뒤 이 조건에 맞지 않게 된 카드는 목록에서 숨긴다.
  bool matches(SavedItem item) =>
      (folderId == null || item.folder?.id == folderId) &&
      (!unreadOnly || !item.isRead);

  SavedQuery copyWith({
    String? Function()? folderId,
    bool? unreadOnly,
    SavedSort? sort,
  }) => SavedQuery(
    folderId: folderId == null ? this.folderId : folderId(),
    unreadOnly: unreadOnly ?? this.unreadOnly,
    sort: sort ?? this.sort,
  );
}

class SavedState {
  const SavedState({
    required this.meta,
    required this.folders,
    required this.query,
    required this.items,
    this.nextCursor,
    this.reloading = false,
    this.loadingMore = false,
    this.listError,
  });

  /// 폴더 이름·메모 길이 상한과 재알림 일수.
  final Meta meta;
  final FolderList folders;
  final SavedQuery query;

  /// 불러온 카드. 쓰기로 조건에서 벗어난 카드도 되돌릴 수 있게 남겨 두고 [visible] 이 거른다.
  final List<SavedItem> items;
  final String? nextCursor;

  /// 조건을 바꿔 첫 페이지를 다시 받는 중.
  final bool reloading;
  final bool loadingMore;

  /// 목록 조회 실패. 폴더 칩은 그대로 두고 목록 자리에만 오류를 보인다.
  final Object? listError;

  List<SavedItem> get visible => items.where(query.matches).toList();

  SavedState copyWith({
    FolderList? folders,
    SavedQuery? query,
    List<SavedItem>? items,
    String? Function()? nextCursor,
    bool? reloading,
    bool? loadingMore,
    Object? Function()? listError,
  }) => SavedState(
    meta: meta,
    folders: folders ?? this.folders,
    query: query ?? this.query,
    items: items ?? this.items,
    nextCursor: nextCursor == null ? this.nextCursor : nextCursor(),
    reloading: reloading ?? this.reloading,
    loadingMore: loadingMore ?? this.loadingMore,
    listError: listError == null ? this.listError : listError(),
  );
}

final savedControllerProvider =
    AsyncNotifierProvider<SavedController, SavedState>(SavedController.new);

class SavedController extends AsyncNotifier<SavedState> {
  /// 조건을 빨리 바꿀 때 늦게 온 이전 응답을 버린다.
  int _generation = 0;

  SavedRepository get _repo => ref.read(savedRepositoryProvider);

  SavedState get _current => state.requireValue;

  void _set(SavedState Function(SavedState s) change) {
    if (ref.mounted && state.hasValue) state = AsyncData(change(_current));
  }

  @override
  Future<SavedState> build() async {
    final repo = ref.watch(savedRepositoryProvider);
    final meta = ref.watch(metaRepositoryProvider).meta();
    final folders = repo.folders();
    final page = repo.saved();
    await Future.wait([meta, folders, page]);
    return SavedState(
      meta: await meta,
      folders: await folders,
      query: const SavedQuery(),
      items: (await page).items,
      nextCursor: (await page).nextCursor,
    );
  }

  // ── 조회 ──

  Future<void> selectFolder(String? folderId) =>
      _reload(_current.query.copyWith(folderId: () => folderId));

  Future<void> toggleUnreadOnly() =>
      _reload(_current.query.copyWith(unreadOnly: !_current.query.unreadOnly));

  Future<void> setSort(SavedSort sort) =>
      _reload(_current.query.copyWith(sort: sort));

  /// 당겨서 새로고침 — 폴더 칩과 첫 페이지를 다시 받는다.
  Future<void> refresh() => _reload(_current.query, withFolders: true);

  /// 목록 오류의 `다시 시도`.
  Future<void> retry() => _reload(_current.query);

  Future<void> _reload(SavedQuery query, {bool withFolders = false}) async {
    final generation = ++_generation;
    _set(
      (s) => s.copyWith(
        query: query,
        items: const [],
        nextCursor: () => null,
        reloading: true,
        loadingMore: false,
        listError: () => null,
      ),
    );
    try {
      final pageFuture = _repo.saved(
        folderId: query.folderId,
        unreadOnly: query.unreadOnly,
        sort: query.sort,
      );
      final foldersFuture = withFolders
          ? _repo.folders()
          : Future.value(_current.folders);
      await Future.wait([pageFuture, foldersFuture]);
      final page = await pageFuture;
      final folders = await foldersFuture;
      if (generation != _generation) return;
      _set(
        (s) => s.copyWith(
          folders: folders,
          items: page.items,
          nextCursor: () => page.nextCursor,
          reloading: false,
        ),
      );
    } catch (e) {
      if (generation != _generation) return;
      _set((s) => s.copyWith(reloading: false, listError: () => e));
    }
  }

  /// 무한 스크롤 — 다음 커서가 있으면 이어 붙인다. 실패는 조용히 멈추고 다음 스크롤에 다시 시도한다.
  Future<void> loadMore() async {
    final s = _current;
    final cursor = s.nextCursor;
    if (cursor == null || s.reloading || s.loadingMore) return;
    final generation = _generation;
    _set((s) => s.copyWith(loadingMore: true));
    try {
      final page = await _repo.saved(
        folderId: s.query.folderId,
        unreadOnly: s.query.unreadOnly,
        sort: s.query.sort,
        cursor: cursor,
      );
      if (generation != _generation) return;
      _set(
        (s) => s.copyWith(
          items: [...s.items, ...page.items],
          nextCursor: () => page.nextCursor,
          loadingMore: false,
        ),
      );
    } catch (_) {
      if (generation == _generation) {
        _set((s) => s.copyWith(loadingMore: false));
      }
    }
  }

  // ── 찜 쓰기 ──

  Future<void> moveToFolder(SavedItem item, FolderRef? folder) => _patch(
    item,
    item.copyWith(folder: () => folder),
    SavedItemPatch.folder(folder?.id),
  );

  /// 공백뿐이면 메모를 지운다 (계약 4.7 — 빈 문자열은 `null`).
  Future<void> editMemo(SavedItem item, String memo) {
    final text = memo.trim();
    final value = text.isEmpty ? null : text;
    return _patch(
      item,
      item.copyWith(memo: () => value),
      SavedItemPatch.memo(value),
    );
  }

  /// 원문 열기·07 이동 때 부른다. 이미 읽었으면 보내지 않는다.
  Future<void> markRead(SavedItem item) async {
    if (item.isRead) return;
    await _patch(
      item,
      item.copyWith(isRead: true, readAt: () => DateTime.now().toUtc()),
      const SavedItemPatch.read(),
    );
  }

  Future<void> _patch(
    SavedItem before,
    SavedItem after,
    SavedItemPatch patch,
  ) async {
    _replace(after);
    try {
      _replace(await _repo.update(before.alertId, patch));
    } catch (_) {
      _replace(before);
      rethrow;
    }
    await _refreshFolders();
  }

  void _replace(SavedItem item) => _set(
    (s) => s.copyWith(
      items: [for (final i in s.items) i.alertId == item.alertId ? item : i],
    ),
  );

  /// 찜 해제. 되돌리기에 쓸 원래 자리를 돌려준다.
  Future<int> unsave(SavedItem item) async {
    final index = _current.items.indexWhere((i) => i.alertId == item.alertId);
    _set(
      (s) => s.copyWith(
        items: s.items.where((i) => i.alertId != item.alertId).toList(),
      ),
    );
    try {
      await _repo.unsave(item.alertId);
    } catch (_) {
      _insert(item, index);
      rethrow;
    }
    await _refreshFolders();
    return index;
  }

  /// 되돌리기 — 같은 폴더·메모·읽음으로 다시 찜하고 원래 자리에 넣는다 (계약 4.7 `DELETE`).
  Future<void> undoUnsave(SavedItem item, int index) async {
    var restored = await _repo.save(item.alertId, folderId: item.folder?.id);
    if (item.memo != null) {
      restored = await _repo.update(
        item.alertId,
        SavedItemPatch.memo(item.memo),
      );
    }
    if (item.isRead) {
      restored = await _repo.update(item.alertId, const SavedItemPatch.read());
    }
    _insert(restored, index);
    await _refreshFolders();
  }

  void _insert(SavedItem item, int index) => _set(
    (s) => s.copyWith(
      items: [...s.items]..insert(index.clamp(0, s.items.length), item),
    ),
  );

  // ── 폴더 쓰기 ──

  Future<Folder> createFolder(String name) async {
    final folder = await _repo.createFolder(name);
    await _refreshFolders();
    return folder;
  }

  Future<void> renameFolder(String folderId, String name) async {
    final folder = await _repo.updateFolder(folderId, name: name);
    _set(
      (s) => s.copyWith(
        items: [
          for (final i in s.items)
            i.folder?.id == folderId ? i.copyWith(folder: () => folder.ref) : i,
        ],
      ),
    );
    await _refreshFolders();
  }

  /// 안의 찜은 미분류가 된다. 보고 있던 폴더면 `전체` 로 돌아간다.
  Future<void> deleteFolder(String folderId) async {
    await _repo.deleteFolder(folderId);
    _set(
      (s) => s.copyWith(
        items: [
          for (final i in s.items)
            i.folder?.id == folderId ? i.copyWith(folder: () => null) : i,
        ],
      ),
    );
    if (_current.query.folderId == folderId) {
      await _reload(
        _current.query.copyWith(folderId: () => null),
        withFolders: true,
      );
    } else {
      await _refreshFolders();
    }
  }

  /// 폴더 순서를 [position] 으로 옮긴다. 칩 순서를 먼저 바꾸고 실패하면 되돌린다.
  Future<void> moveFolder(String folderId, int position) async {
    final before = _current.folders;
    final folders = [...before.folders];
    final folder = folders.removeAt(
      folders.indexWhere((f) => f.id == folderId),
    );
    folders.insert(position.clamp(0, folders.length), folder);
    _set(
      (s) => s.copyWith(
        folders: FolderList(
          totalCount: before.totalCount,
          unreadCount: before.unreadCount,
          unfiledCount: before.unfiledCount,
          folders: folders,
        ),
      ),
    );
    try {
      await _repo.updateFolder(folderId, position: position);
    } catch (_) {
      _set((s) => s.copyWith(folders: before));
      rethrow;
    }
    await _refreshFolders();
  }

  Future<void> _refreshFolders() async {
    final folders = await _repo.folders();
    _set((s) => s.copyWith(folders: folders));
  }
}
