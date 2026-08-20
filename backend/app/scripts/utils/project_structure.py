import os
from pathlib import Path
import pathspec

# Укажите путь к папке, которую нужно отсканировать
target_folder = r'D:\lang_tutor_project'
output_filename = 'full_structure.txt'

# Путь к файлу .gitignore (предполагаем, что он лежит в корне целевой папки)
gitignore_path = os.path.join(target_folder, '.gitignore')

# 1. Загружаем и компилируем правила .gitignore
if os.path.exists(gitignore_path):
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        # Читаем строки и создаем спецификацию шаблонов (игнорируем пустые строки и комментарии)
        spec = pathspec.PathSpec.from_lines('gitwildmatch', f.readlines())
else:
    print("Файл .gitignore не найден. Скрипт выполнится без фильтрации.")
    spec = None

with open(output_filename, 'w', encoding='utf-8') as f:
    for root, dirs, files in os.walk(target_folder):

        # 2. Фильтруем директории на месте (in-place modification для os.walk)
        # Это предотвращает заход os.walk в папки типа venv или node_modules, ускоряя работу
        if spec:
            # Для pathspec важно передавать относительный путь с правильными слэшами
            remaining_dirs = []
            for d in dirs:
                # Получаем относительный путь к папке и добавляем слэш в конец,
                # чтобы pathspec понимал, что это директория
                rel_dir_path = os.path.relpath(os.path.join(root, d), target_folder) + '/'
                if not spec.match_file(rel_dir_path):
                    remaining_dirs.append(d)

            # Изменяем список dirs, чтобы os.walk не шел в игнорируемые папки
            dirs[:] = remaining_dirs

        # Записываем текущую папку (вычисляем относительный путь для красоты)
        rel_root = os.path.relpath(root, target_folder)
        f.write(f"\nПапка: {rel_root if rel_root != '.' else 'Корень'}\n")
        f.write("-" * 40 + "\n")

        # 3. Записываем файлы, предварительно отфильтровав их
        for file in files:
            rel_file_path = os.path.relpath(os.path.join(root, file), target_folder)

            # Если файл подпадает под правила gitignore — пропускаем его
            if spec and spec.match_file(rel_file_path):
                continue

            f.write(f"  Файл: {file}\n")

print(f"Полная структура (с учетом .gitignore) успешно сохранена в {output_filename}")