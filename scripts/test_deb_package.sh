#!/usr/bin/env bash
set -euo pipefail

package_file="${1:?Uso: $0 caminho/para/linguaforge_versao_amd64.deb}"
[[ -f "$package_file" ]] || {
    printf 'Pacote não encontrado: %s\n' "$package_file" >&2
    exit 1
}
for command in dpkg dpkg-deb desktop-file-validate grep install mktemp; do
    command -v "$command" >/dev/null 2>&1 || {
        printf 'Comando necessário não encontrado: %s\n' "$command" >&2
        exit 1
    }
done

test_dir="$(mktemp -d /tmp/linguaforge-deb-test.XXXXXX)"
cleanup() {
    rm -rf -- "$test_dir"
}
trap cleanup EXIT
extract_dir="$test_dir/extracted"
root_dir="$test_dir/root"
admin_dir="$test_dir/admin"
user_data="$test_dir/user-data"

dpkg-deb --extract "$package_file" "$extract_dir"
desktop-file-validate "$extract_dir/usr/share/applications/linguaforge.desktop"
test -x "$extract_dir/usr/bin/linguaforge"
test -x "$extract_dir/opt/linguaforge/app/linguaforge-preview"
test -f "$extract_dir/usr/share/icons/hicolor/scalable/apps/linguaforge.svg"
if find "$extract_dir/opt/linguaforge/app" -path '*/models/*' -o -path '*/llama.cpp/*' | grep -q .; then
    printf 'O pacote extraído contém modelo ou backend indevido.\n' >&2
    exit 1
fi

install -d "$user_data/linguaforge"
printf 'chat data must survive package operations\n' > "$user_data/linguaforge/sentinel.txt"
install -d "$test_dir/resources/runtime"
touch "$test_dir/resources/model.gguf" "$test_dir/resources/llama-server"
chmod 0755 "$test_dir/resources/llama-server"
XDG_DATA_HOME="$user_data" XDG_CONFIG_HOME="$test_dir/user-config" XDG_STATE_HOME="$test_dir/user-state" \
    "$extract_dir/opt/linguaforge/app/linguaforge-preview" --configure-resources \
    --model "$test_dir/resources/model.gguf" --server "$test_dir/resources/llama-server" \
    --cuda-runtime "$test_dir/resources/runtime" > "$test_dir/configure.txt"
XDG_DATA_HOME="$user_data" XDG_CONFIG_HOME="$test_dir/user-config" XDG_STATE_HOME="$test_dir/user-state" \
    "$extract_dir/opt/linguaforge/app/linguaforge-preview" --check > "$test_dir/check.json"
grep -Fq "$extract_dir/opt/linguaforge/app/_internal/frontend" "$test_dir/check.json"
grep -Fq "$test_dir/resources/model.gguf" "$test_dir/check.json"

install -d "$root_dir" "$admin_dir"
touch "$admin_dir/status"
dpkg --root="$root_dir" --admindir="$admin_dir" --log="$test_dir/dpkg.log" \
    --force-depends --force-not-root --force-script-chrootless -i "$package_file"
test -x "$root_dir/usr/bin/linguaforge"
test -x "$root_dir/opt/linguaforge/app/linguaforge-preview"

# Simula uma atualização sem instalar nada no sistema real.
dpkg-deb --raw-extract "$package_file" "$test_dir/update-source"
sed -i 's/^Version: .*/Version: 0.1.0+test1/' "$test_dir/update-source/DEBIAN/control"
dpkg-deb --root-owner-group --build "$test_dir/update-source" "$test_dir/linguaforge-update.deb"
dpkg --root="$root_dir" --admindir="$admin_dir" --log="$test_dir/dpkg.log" \
    --force-depends --force-not-root --force-script-chrootless -i "$test_dir/linguaforge-update.deb"
dpkg --root="$root_dir" --admindir="$admin_dir" -s linguaforge | grep -Fq 'Version: 0.1.0+test1'

dpkg --root="$root_dir" --admindir="$admin_dir" --log="$test_dir/dpkg.log" \
    --force-not-root --force-script-chrootless --purge linguaforge
test ! -e "$root_dir/opt/linguaforge"
test ! -e "$root_dir/usr/bin/linguaforge"
test -f "$user_data/linguaforge/sentinel.txt"
printf 'Pacote validado: extração, instalação isolada, atualização e remoção preservaram dados do usuário.\n'
