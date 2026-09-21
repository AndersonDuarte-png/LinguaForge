#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
desktop_python="$project_dir/.venv-desktop/bin/python"

for command in dpkg dpkg-deb desktop-file-validate install; do
    command -v "$command" >/dev/null 2>&1 || {
        printf 'Comando necessário não encontrado: %s\n' "$command" >&2
        exit 1
    }
done
[[ -x "$desktop_python" ]] || {
    printf 'Ambiente desktop ausente: %s\n' "$desktop_python" >&2
    exit 1
}
[[ "$(dpkg --print-architecture)" == "amd64" ]] || {
    printf 'Este pacote inicial suporta apenas amd64.\n' >&2
    exit 1
}

version="$($desktop_python -c 'import tomllib; from pathlib import Path; print(tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"])')"
package_name="linguaforge_${version}_amd64"
stage_dir="$project_dir/build/$package_name"
package_file="$project_dir/dist/$package_name.deb"

"$project_dir/scripts/build_desktop_preview.sh"
rm -rf -- "$stage_dir"
install -d -m 0755 "$stage_dir/DEBIAN" "$stage_dir/opt/linguaforge/app" \
    "$stage_dir/usr/bin" "$stage_dir/usr/share/applications" "$stage_dir/usr/share/icons/hicolor/scalable/apps"
sed "s/@VERSION@/$version/" "$project_dir/packaging/debian/control.in" > "$stage_dir/DEBIAN/control"
install -m 0755 "$project_dir/packaging/debian/linguaforge" "$stage_dir/usr/bin/linguaforge"
install -m 0644 "$project_dir/packaging/debian/linguaforge.desktop" "$stage_dir/usr/share/applications/linguaforge.desktop"
install -m 0644 "$project_dir/packaging/debian/linguaforge.svg" "$stage_dir/usr/share/icons/hicolor/scalable/apps/linguaforge.svg"
cp -a "$project_dir/dist/linguaforge-preview/." "$stage_dir/opt/linguaforge/app/"

desktop-file-validate "$stage_dir/usr/share/applications/linguaforge.desktop"
dpkg-deb --root-owner-group --build "$stage_dir" "$package_file"
dpkg-deb --info "$package_file"
contents_file="$stage_dir/package-contents.txt"
dpkg-deb --contents "$package_file" > "$contents_file"
grep -Fq 'usr/share/applications/linguaforge.desktop' "$contents_file"
grep -Fq 'usr/share/icons/hicolor/scalable/apps/linguaforge.svg' "$contents_file"
if grep -Eq '/models/|llama\.cpp/' "$contents_file"; then
    printf 'O pacote não pode incluir modelo ou backend local.\n' >&2
    exit 1
fi
printf 'Pacote criado: %s\n' "$package_file"
