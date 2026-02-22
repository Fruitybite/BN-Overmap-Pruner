# BN-Overmap-Pruner
[카타클리즘: 밝은 밤](https://github.com/cataclysmbn/Cataclysm-BN)용 오버맵 청소기입니다. V2 포맷 세이브 파일에 맞게 만들어졌습니다. 본인 책임 하에 사용하세요.

[하늘섬](https://github.com/graysonchao/CBN-Sky-Island) 모드와 쓰려고 만들었지만, 다른 용도로도 쓸만할지 모릅니다.

LLM의 도움을 받아 만들었으므로 너무 신뢰하면 곤란합니다.

이 툴을 개선할만한 아이디어가 있다면 자유롭게 풀 리퀘스트를 넣으시고 밝은밤 디스코드에서 절 호출해주세요.

## 사용법
0. **사용 전에 반드시 백업할 것**
   - 업로드 전에 테스트는 마쳤지만, 치명적인 오류가 발생하거나 세이브 파일이 오염될 수도 있습니다.
 1. 파일을 다운받아서 세이브 파일 경로에 넣으세요.
 2. 다음 경로에서 파이썬을 설치하세요. https://www.python.org/
    - 저는 3.10.8 버전을 쓰고 있지만, 최신 버전이면 다 잘 돌아갈겁니다.
 3. 인게임 오버맵 좌표 옵션을 절대값으로 설정하세요.
 4. 보존하고 싶은 서브맵 좌표를 기록해두세요.
 5. 세이브 파일 경로에서 명령 프롬프트나 윈도우 터미널을 여세요.
 6. 좌표와 함께 적절한 명령어를 입력하세요.
    - 중요사항 : 이 툴은 사전에 입력하지 않은 **모든** 오버맵 및 서브맵을 삭제합니다.
    - 자동 백업 : 이 툴은 작동 과정에서 `map.sqlite3.bak` (또는 비슷한 확장자로) 자동 백업 파일을 동일한 경로에 만듭니다. 뭔가 문제가 생기면 찾아서 확장자를 바꾸면 됩니다. 그렇지만 이 기능에만 의존하지 말고, 직접 백업해둘 것을 강력하게 권장합니다.

## 명령어

`overmap_pruner.py [-h] (--keep KEEP | --keep-file KEEP_FILE | --interactive) [--span SPAN] [--no-vacuum] [--dry-run] [--force] [--remove-grids] [--verify-against VERIFY_AGAINST] [--verify-only] [db]`

  **--keep KEEP** : 원하는 좌표를 직접 입력합니다.
  
  전체 좌표를 큰따옴표 ("") 로 묶습니다. 마침표(.) 는 단일 좌표에서 X, Y, Z축을 구분하는데 쓰입니다. 쉼표 (,) 는 둘 이상의 좌표를 서로 구분하는데 쓰입니다.
  
  예를 들어 `"119.183.9, 119.183.10"` 이라는 값은 오버맵 좌표 옵션을 "절대값"으로 설정했을 때 기준으로 두 서브맵 `119,183,9` 및 `119,183,10` 을 의미합니다.
  
  e.g.) `python overmap_pruner.py --keep "119.183.9"`
  
  **--keep-file KEEP_FILE** : 원하는 좌표를 별도 파일에 입력한 다음 청소기를 실행할 때 해당 파일을 함께 입력합니다.
  
  한 줄에 좌표를 하나씩 작성하세요. `--keep` 옵션과 같지만, 좌표 입력 과정에서 실수할 가능성이 더 낮아지므로 이 방법을 권장합니다.

  e.g.) `python overmap_pruner.py --keep-file keep.txt`
  
  **--interactive** :  원하는 좌표를 직접 입력합니다.

  `--keep` 옵션과 유사하지만, 명령어 입력 후 좌표를 별도로 직접 입력할 것을 요구합니다.

  e.g.) `python overmap_pruner.py --interactive`

  **--span SPAN** : 좌표 범위를 입력합니다.

  e.g.) `python overmap_pruner.py --span 180`
  
  밝은밤의 오버맵 좌표 범위 기준값은 180이고, 따라서 이 옵션의 기본값도 180입니다. 당분간 이게 바뀔 일은 없을테니 이 값은 가급적 건드리지 마세요.

  **--no-vacuum** : `VACUUM` 과정을 생략합니다.

  sqlite3 편집 과정에서 데이터를 최적화하는 `VACUUM` 과정을 생략합니다. 작업이 빨라지지만, 이 옵션을 적용하지 않았을 때에 비해 세이브 파일 용량이 커질 수 있습니다.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --no-vacuum`

  **--dry-run** : 청소 계획을 보여주되, 실제 파일은 편집하지 않습니다.

  보존되는 서브맵 좌표 및 오버맵을 표시하지만, 실제로 파일을 편집하지는 않습니다. 테스트 용도로 적합합니다.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --dry-run`

  **--force** : 확인 절차를 생략합니다.

  백업 파일을 만들어둔게 아니라면 함부로 쓰면 안됩니다.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --force`

  **--remove-grid** : 보존된 오버맵에 존재하는 모든 전력망/수도망 데이터를 제거합니다.

  기본값은 오버맵의 전력망/수도망 데이터를 오버맵 파일과 별도로 보존해서 한번 더 덮어쓰는 것입니다. 이 옵션을 활성화하면 오류를 일으킬 수 있고, 데이터가 제대로 제거되지 않을 수도 있습니다.
  
   꼭 필요한 경우에만 사용하세요.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --remove-grid`

  **--verify-against VERIFY_AGAINST** : `map.sqlite3` 파일과 다른 `map.sqlite3` 파일을 비교 및 검증합니다.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --verify-against map_old.sqlite3`

  **--verify-only** : `--verify-against` 옵션과 함께 사용하여 검증 과정만 진행하고 청소 절차는 진행하지 않습니다.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --verify-against map_old.sqlite3 --verify-only`

  **db** : `map.sqlite3` 파일의 경로입니다.

  별도로 제시되지 않으면 툴이 위치한 폴더 내에서 `map.sqlite3` 파일을 찾아 사용하려 시도할 것입니다.
