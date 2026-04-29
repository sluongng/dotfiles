#!/usr/bin/env bash

set -euo pipefail

workspace="${MBT_WORKSPACE:-$(pwd)}"
output_file="${MBT_OUTPUT_FILE:-$workspace/.metals/mbt.json}"
default_query_roots='//src:all + //src/main/java/... + //src/main/protobuf/... + //src/test/java/... + //src/java_tools/... + //src/tools/... + //examples/... + //third_party/... + //tools/build_defs/build_info:all + //tools/test/CoverageOutputGenerator/...'
default_query_excluded='//tools/build_defs/build_info:all + //src/test/java/com/google/devtools/build/lib/blackbox/tests:black_box_tests + //src/java_tools/buildjar/java/com/google/devtools/build/buildjar:starlark-deps + //src/java_tools/buildjar/java/com/google/devtools/build/buildjar/javac/plugins:bootstrap_plugins + //src/java_tools/buildjar:bootstrap_VanillaJavaBuilder_deploy.jar + //src/java_tools/buildjar/java/com/google/devtools/build/buildjar/genclass:bootstrap_genclass + //src/java_tools/buildjar/java/com/google/devtools/build/buildjar:bootstrap_VanillaJavaBuilder + //src/java_tools/buildjar/java/com/google/devtools/build/buildjar/jarhelper:bootstrap_jarhelper + //src/java_tools/buildjar:bootstrap_genclass_deploy.jar + //src/java_tools/junitrunner/javatests/com/google/testing/coverage:all + //examples/java-starlark/...'
default_query='kind("java_.* rule", ('"$default_query_roots"') except ('"$default_query_excluded"'))'
bazel_query="${MBT_BAZEL_QUERY:-$default_query}"
transitive_bazel_query="${MBT_BAZEL_TRANSITIVE_QUERY:-kind(\"java_.* rule\", deps($bazel_query))}"
build_batch_size="${MBT_BAZEL_BUILD_BATCH_SIZE:-400}"
maven_sources_dir="${MBT_MAVEN_SOURCES_DIR:-$workspace/.metals/mbt-source-jars}"
maven_repository="${MBT_MAVEN_REPOSITORY:-https://repo1.maven.org/maven2}"

if ! command -v bazel >/dev/null 2>&1; then
  echo "bazel.mbt.sh: bazel is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "bazel.mbt.sh: jq is required" >&2
  exit 1
fi

detect_java_home() {
  if [[ -n "${MBT_JAVA_HOME:-}" && -x "$MBT_JAVA_HOME/bin/java" && -f "$MBT_JAVA_HOME/lib/src.zip" ]]; then
    printf '%s\n' "$MBT_JAVA_HOME"
    return
  fi

  if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" && -f "$JAVA_HOME/lib/src.zip" ]]; then
    printf '%s\n' "$JAVA_HOME"
    return
  fi

  for home in \
    /usr/lib/jvm/java-25-openjdk \
    /usr/lib/jvm/java-21-openjdk \
    /usr/lib/jvm/java-17-openjdk \
    /usr/lib/jvm/default \
    /usr/lib/jvm/java-25-graalvm-ce; do
    if [[ -x "$home/bin/java" && -f "$home/lib/src.zip" ]]; then
      printf '%s\n' "$home"
      return
    fi
  done

  if [[ -x /usr/lib/jvm/default/bin/java ]]; then
    printf '%s\n' /usr/lib/jvm/default
    return
  fi

  local java_bin
  java_bin="$(command -v java || true)"
  if [[ -n "$java_bin" ]]; then
    readlink -f "$java_bin" | sed 's#/bin/java$##'
  fi
}

discover_sources() {
  if [[ -n "${MBT_SOURCE_ROOTS:-}" ]]; then
    printf '%s\n' "${MBT_SOURCE_ROOTS//:/$'\n'}"
    return
  fi

  if git -C "$workspace" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$workspace" ls-files '*.java' | while IFS= read -r source_file; do
      local package_name package_path source_dir source_root
      package_name="$(
        sed -nE '
          s/^[[:space:]]*package[[:space:]]+([A-Za-z_][A-Za-z0-9_.]*)[[:space:]]*;.*/\1/p
          /^[[:space:]]*(import|public|class|interface|enum|@)/q
        ' "$workspace/$source_file" | head -n 1
      )"
      source_dir="${source_file%/*}"
      if [[ "$source_dir" == "$source_file" ]]; then
        source_dir="."
      fi

      if [[ -n "$package_name" ]]; then
        package_path="${package_name//./\/}"
        if [[ "$source_dir" == "$package_path" ]]; then
          source_root="."
        elif [[ "$source_dir" == */"$package_path" ]]; then
          source_root="${source_dir%/$package_path}"
        else
          source_root="$source_dir"
        fi
      else
        source_root="$source_dir"
      fi

      printf '%s\n' "$source_root"
    done
    return
  fi

  find "$workspace" -name '*.java' -type f | sed "s#^$workspace/##"
}

abs_path() {
  if [[ "$1" = /* ]]; then
    printf '%s\n' "$1"
  else
    printf '%s\n' "$workspace/$1"
  fi
}

write_existing_abs_paths() {
  local path absolute_path
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    absolute_path="$(abs_path "$path")"
    if [[ -e "$absolute_path" ]]; then
      printf '%s\n' "$absolute_path"
    fi
  done
}

write_existing_source_pairs() {
  local jar source jar_abs source_abs
  while IFS=$'\t' read -r jar source; do
    [[ -n "$jar" && -n "$source" ]] || continue
    jar_abs="$(abs_path "$jar")"
    source_abs="$(abs_path "$source")"
    if [[ -e "$jar_abs" && -e "$source_abs" ]]; then
      printf '%s\t%s\n' "$jar_abs" "$source_abs"
    fi
  done
}

download_file() {
  local url="$1"
  local output="$2"

  mkdir -p "$(dirname "$output")"
  if command -v curl >/dev/null 2>&1; then
    curl -fLs "$url" -o "$output"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$url" -O "$output"
  else
    echo "bazel.mbt.sh: curl or wget is required to fetch Maven source jars" >&2
    return 1
  fi
}

maven_source_for_rules_jvm_external_jar() {
  local jar="$1"
  local marker="/external/rules_jvm_external++maven+maven/"
  if [[ "$jar" != *"$marker"* ]]; then
    return 1
  fi

  local relative dir version artifact_dir artifact group_path source_name source_path source_url
  relative="${jar#*"$marker"}"
  dir="${relative%/*}"
  version="${dir##*/}"
  artifact_dir="${dir%/*}"
  artifact="${artifact_dir##*/}"
  group_path="${artifact_dir%/*}"
  source_name="${artifact}-${version}-sources.jar"
  source_path="$maven_sources_dir/$group_path/$artifact/$version/$source_name"
  source_url="${maven_repository%/}/$group_path/$artifact/$version/$source_name"

  if [[ ! -e "$source_path" ]]; then
    local tmp_source="${source_path}.tmp.$$"
    if download_file "$source_url" "$tmp_source"; then
      mv "$tmp_source" "$source_path"
    else
      rm -f "$tmp_source"
      return 1
    fi
  fi

  printf '%s\n' "$source_path"
}

write_maven_source_pairs() {
  local jar jar_abs source_abs
  while IFS= read -r jar; do
    [[ -n "$jar" ]] || continue
    jar_abs="$(abs_path "$jar")"
    source_abs="$(maven_source_for_rules_jvm_external_jar "$jar_abs" || true)"
    if [[ -n "$source_abs" && -e "$source_abs" ]]; then
      printf '%s\t%s\n' "$jar_abs" "$source_abs"
    fi
  done
}

write_config_matched_source_pairs() {
  local pairs_file="$1"
  local jar source jar_abs source_abs suffix
  declare -A existing_sources_by_jar=()
  declare -A sources_by_output_suffix=()

  while IFS=$'\t' read -r jar source; do
    [[ -n "$jar" && -n "$source" ]] || continue
    jar_abs="$(abs_path "$jar")"
    source_abs="$(abs_path "$source")"
    [[ -e "$jar_abs" && -e "$source_abs" ]] || continue

    existing_sources_by_jar["$jar_abs"]=1
    if [[ "$jar_abs" == */bin/* ]]; then
      suffix="${jar_abs#*/bin/}"
      sources_by_output_suffix["$suffix"]="$source_abs"
    fi
  done <"$pairs_file"

  while IFS= read -r jar; do
    [[ -n "$jar" ]] || continue
    jar_abs="$(abs_path "$jar")"
    [[ -e "$jar_abs" && -z "${existing_sources_by_jar[$jar_abs]:-}" ]] || continue
    [[ "$jar_abs" == */bin/* ]] || continue

    suffix="${jar_abs#*/bin/}"
    source_abs="${sources_by_output_suffix[$suffix]:-}"
    if [[ -n "$source_abs" && -e "$source_abs" ]]; then
      printf '%s\t%s\n' "$jar_abs" "$source_abs"
    fi
  done
}

java_home="$(detect_java_home)"
if [[ -z "$java_home" ]]; then
  echo "bazel.mbt.sh: could not find a Java home" >&2
  exit 1
fi
export JAVA_HOME="$java_home"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/bazel-mbt.XXXXXXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT

cquery_format="$tmp_dir/java_info.cquery.star"
query_labels_file="$tmp_dir/query_labels.txt"
top_query_file="$tmp_dir/top_labels.cquery"
transitive_query_file="$tmp_dir/transitive_labels.cquery"
top_java_info_jsonl="$tmp_dir/top_java_info.jsonl"
transitive_java_info_jsonl="$tmp_dir/transitive_java_info.jsonl"
labels_file="$tmp_dir/labels.txt"
runtime_jars_file="$tmp_dir/runtime_jars.txt"
source_pairs_file="$tmp_dir/source_pairs.tsv"
maven_source_pairs_file="$tmp_dir/maven_source_pairs.tsv"
runtime_jars_json="$tmp_dir/runtime_jars.json"
source_pairs_json="$tmp_dir/source_pairs.json"
sources_json="$tmp_dir/sources.json"

cat >"$cquery_format" <<'EOF'
def _java_info(target):
    providers_dict = providers(target)
    for key in providers_dict.keys():
        if key.endswith("%JavaInfo"):
            return providers_dict[key]
    return None

def _paths(value):
    if value == None:
        return []
    if type(value) == "depset":
        value = value.to_list()
    return [f.path for f in value]

def _label_string(label):
    value = str(label)
    if value.startswith("@@//"):
        return value[2:]
    return value

def format(target):
    java_info = _java_info(target)
    if java_info == None:
        return ""

    return json.encode({
        "label": _label_string(target.label),
        "direct_jars": _paths(java_info.full_compile_jars),
        "direct_sources": _paths(java_info.source_jars),
        "target_jars": _paths(target.files),
        "runtime_jars": _paths(java_info.transitive_runtime_jars),
    })
EOF

resolve_query_labels() {
  local query="$1"
  local output="$2"
  local description="$3"

  echo "bazel.mbt.sh: resolving $description labels with: $query" >&2
  set +e
  (cd "$workspace" && bazel query --keep_going "$query") | sort -u >"$output"
  local pipeline_status=("${PIPESTATUS[@]}")
  local query_status="${pipeline_status[0]}"
  local sort_status="${pipeline_status[1]}"
  set -e

  if [[ "$sort_status" -ne 0 ]]; then
    echo "bazel.mbt.sh: failed to sort Bazel query output for $description" >&2
    exit "$sort_status"
  fi

  if [[ "$query_status" -ne 0 ]]; then
    echo "bazel.mbt.sh: Bazel query for $description reported errors; continuing with matched labels" >&2
  fi
}

write_label_set_query() {
  local labels="$1"
  local output="$2"
  local expression_prefix="${3:-}"
  local expression_suffix="${4:-}"

  {
    printf '%sset(\n' "$expression_prefix"
    sed 's/$/ /' "$labels"
    printf ')%s\n' "$expression_suffix"
  } >"$output"
}

run_java_info_cquery_file() {
  local query_file="$1"
  local output="$2"
  local description="$3"

  echo "bazel.mbt.sh: querying $description JavaInfo with labels from: $query_file" >&2
  set +e
  (cd "$workspace" && bazel cquery --keep_going --query_file="$query_file" --output=starlark --starlark:file="$cquery_format") \
    | jq -c 'select(type == "object")' >"$output"
  local pipeline_status=("${PIPESTATUS[@]}")
  local cquery_status="${pipeline_status[0]}"
  local jq_status="${pipeline_status[1]}"
  set -e

  if [[ "$jq_status" -ne 0 ]]; then
    echo "bazel.mbt.sh: failed to parse Bazel cquery output for $description" >&2
    exit "$jq_status"
  fi

  if [[ "$cquery_status" -ne 0 ]]; then
    echo "bazel.mbt.sh: Bazel cquery for $description reported errors; continuing with successfully analyzed targets" >&2
  fi
}

resolve_query_labels "$bazel_query" "$query_labels_file" "top-level"
write_label_set_query "$query_labels_file" "$top_query_file"
write_label_set_query "$query_labels_file" "$transitive_query_file" 'kind("java_.* rule", deps(' '))'

run_java_info_cquery_file "$top_query_file" "$top_java_info_jsonl" "top-level"

if [[ ! -s "$top_java_info_jsonl" ]]; then
  echo "bazel.mbt.sh: Bazel cquery did not return any top-level JavaInfo targets" >&2
  exit 1
fi

if [[ -n "${MBT_BAZEL_TRANSITIVE_QUERY:-}" ]]; then
  echo "$transitive_bazel_query" >"$transitive_query_file"
fi

run_java_info_cquery_file "$transitive_query_file" "$transitive_java_info_jsonl" "transitive"

if [[ ! -s "$transitive_java_info_jsonl" ]]; then
  echo "bazel.mbt.sh: transitive JavaInfo query returned no targets; using top-level source pairs only" >&2
  cp "$top_java_info_jsonl" "$transitive_java_info_jsonl"
fi

jq -r '.label' "$top_java_info_jsonl" | sort -u >"$labels_file"

if [[ "${MBT_SKIP_BAZEL_BUILD:-0}" != "1" ]]; then
  echo "bazel.mbt.sh: materializing Java jars and source jars" >&2
  set +e
  (cd "$workspace" && xargs -r -n "$build_batch_size" bazel build --keep_going --output_groups=+_source_jars -- <"$labels_file")
  build_status="$?"
  set -e
  if [[ "$build_status" -ne 0 ]]; then
    echo "bazel.mbt.sh: Bazel build reported errors; continuing with jars that were materialized" >&2
  fi
fi

jq -r '.runtime_jars[]?' "$top_java_info_jsonl" | sort -u >"$runtime_jars_file"

jq -r '
  select((.direct_sources | length) == 1)
  | (if (.target_jars | length) == 1 then .target_jars else .direct_jars end) as $jars
  | select(($jars | length) == 1)
  | [$jars[0], .direct_sources[0]]
  | @tsv
' "$transitive_java_info_jsonl" | sort -u >"$source_pairs_file"

if [[ "${MBT_FETCH_MAVEN_SOURCES:-1}" != "0" ]]; then
  write_maven_source_pairs <"$runtime_jars_file" | sort -u >"$maven_source_pairs_file"
  cat "$maven_source_pairs_file" >>"$source_pairs_file"
  sort -u -o "$source_pairs_file" "$source_pairs_file"
fi

write_config_matched_source_pairs "$source_pairs_file" <"$runtime_jars_file" >>"$source_pairs_file"
sort -u -o "$source_pairs_file" "$source_pairs_file"

write_existing_abs_paths <"$runtime_jars_file" \
  | jq -Rn '[inputs | select(length > 0)]' >"$runtime_jars_json"

write_existing_source_pairs <"$source_pairs_file" \
  | jq -Rn '
  reduce inputs as $line ({};
    ($line | split("\t")) as $pair
    | if ($pair | length) == 2 then
        . + {($pair[0]): ($pair[1])}
      else
        .
      end
  )
' >"$source_pairs_json"

discover_sources \
  | sort -u \
  | jq -Rn --arg workspace "$workspace" '
      def abs_path:
        if startswith("/") then . else $workspace + "/" + . end;
      [inputs | select(length > 0) | abs_path]
    ' >"$sources_json"

mkdir -p "$(dirname "$output_file")"

jq -n \
  --arg java_home "$java_home" \
  --slurpfile runtime_jars "$runtime_jars_json" \
  --slurpfile source_pairs "$source_pairs_json" \
  --slurpfile sources "$sources_json" '
  def module_name($jar; $index):
    ($index | tostring) + "_" +
    ($jar
      | gsub("^.*/"; "")
      | gsub("\\.jar$"; "")
      | gsub("[^A-Za-z0-9_.-]+"; "_"));

  def module_id($jar; $index):
    "bazel:" + module_name($jar; $index) + ":local";

  (
    $runtime_jars[0]
    | sort
    | to_entries
    | map({
        id: module_id(.value; .key),
        jar: .value,
        sources: ($source_pairs[0][.value] // null)
      })
  ) as $modules
  |
  {
    dependencyModules: $modules,
    namespaces: {
      java: {
        sources: $sources[0],
        compilerOptions: [],
        dependencyModules: $modules,
        scalaVersion: null,
        javaHome: $java_home,
        dependsOn: []
      }
    }
  }
' >"$output_file"

echo "bazel.mbt.sh: wrote $output_file" >&2
echo "bazel.mbt.sh: $(jq '.namespaces.java.dependencyModules | length' "$output_file") dependency modules" >&2
