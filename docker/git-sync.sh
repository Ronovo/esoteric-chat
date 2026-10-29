#!/bin/sh
set -u

if [ -n "${REPO_URL:-}" ]; then
    (
        cd "${SYNC_DIR:-.}" || exit 1
        [ -d .git ] || git -c init.defaultBranch=main init -q
        if git fetch -q --depth 1 "$REPO_URL" "${REPO_BRANCH:-main}"; then
            git reset -q --hard FETCH_HEAD
            git clean -q -fd
            new=$(git rev-parse HEAD)
            echo "git-sync: running $REPO_URL at $new"
            if [ -n "${BUILD_CMD:-}" ] && [ "$new" != "$(cat .git/git-sync-built 2>/dev/null)" ]; then
                if sh -c "$BUILD_CMD"; then
                    echo "$new" > .git/git-sync-built
                else
                    echo "git-sync: BUILD_CMD failed; it runs again on the next start" >&2
                fi
            fi
        else
            echo "git-sync: could not fetch $REPO_URL; starting with the code already here" >&2
        fi
    )
fi

exec "$@"
