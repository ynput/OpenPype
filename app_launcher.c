/**
This is a simple C equivalent of the `app_launcher.py` with one difference:
it completely detach from the parent process. This is needed to avoid
hanging child processes when the parent process is killed.

You can use it instead of the `app_launcher.py` by building it with:

gcc -std=c99 -o app_launcher app_launcher.c -ljansson

(note you need to have `libjansson` installed - yum install jansson-devel)
**/
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <spawn.h>
#include <sys/wait.h>
#include <string.h>
#include <jansson.h>


int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <json_file>\n", argv[0]);
        return 1;
    }

    json_error_t error;
    json_t *root = json_load_file(argv[1], 0, &error);

    if (!root) {
        fprintf(stderr, "error: on line %d: %s\n", error.line, error.text);
        return 1;
    }

    json_t *env = json_object_get(root, "env");
    char **new_environ = NULL;
    if (json_is_object(env)) {
        const char *key;
        json_t *value;
        int env_size = json_object_size(env);
        new_environ = malloc((env_size + 1) * sizeof(char *));
        int i = 0;

        json_object_foreach(env, key, value) {
            if (json_is_string(value)) {
                char *env_var = malloc(strlen(key) + strlen(json_string_value(value)) + 2);
                sprintf(env_var, "%s=%s", key, json_string_value(value));
                new_environ[i] = env_var;
                i++;
            }
        }
        new_environ[env_size] = NULL;
    }

    json_t *args = json_object_get(root, "args");
    if (json_is_array(args)) {
        char **exec_args = malloc((json_array_size(args) + 2) * sizeof(char *));
        size_t index;
        json_t *value;

        json_array_foreach(args, index, value) {
            if (json_is_string(value)) {
                exec_args[index] = (char *)json_string_value(value);
            }
        }
        exec_args[json_array_size(args)] = NULL;

        posix_spawn_file_actions_t file_actions;
        posix_spawn_file_actions_init(&file_actions);

        posix_spawnattr_t spawnattr;
        posix_spawnattr_init(&spawnattr);

        pid_t pid;
        int status = posix_spawn(&pid, exec_args[0], &file_actions, &spawnattr, exec_args, new_environ);

        if (status == 0) {
            int spawn_status;
            waitpid(pid, &spawn_status, 0);
        } else {
            printf("posix_spawn: %s\n", strerror(status));
        }
        for (int i = 0; i < json_object_size(env); i++) {
            free(new_environ[i]);
        }
        free(exec_args);
    }

    json_decref(root);
    setsid();

    return 0;
}
