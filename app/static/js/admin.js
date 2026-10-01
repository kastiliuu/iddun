document.addEventListener(
  "DOMContentLoaded",
  () => {
    const closeInfoTips = (
      except = null,
    ) => {
      document
        .querySelectorAll(
          (
            "[data-info-trigger]"
            + ".is-open"
          ),
        )
        .forEach((button) => {
          if (button !== except) {
            button.classList.remove(
              "is-open",
            );

            button.setAttribute(
              "aria-expanded",
              "false",
            );
          }
        });
    };

    document
      .querySelectorAll(
        "[data-info-trigger]",
      )
      .forEach((button) => {
        button.addEventListener(
          "click",
          (event) => {
            event.stopPropagation();

            const shouldOpen = (
              !button.classList.contains(
                "is-open",
              )
            );

            closeInfoTips(button);

            button.classList.toggle(
              "is-open",
              shouldOpen,
            );

            button.setAttribute(
              "aria-expanded",
              shouldOpen
                ? "true"
                : "false",
            );
          },
        );
      });

    document.addEventListener(
      "click",
      () => closeInfoTips(),
    );

    document.addEventListener(
      "keydown",
      (event) => {
        if (event.key === "Escape") {
          closeInfoTips();
        }
      },
    );

    document
      .querySelectorAll(
        "[data-image-upload]",
      )
      .forEach((root) => {
        const input = root.querySelector(
          "[data-image-input]",
        );

        const preview = root.querySelector(
          "[data-image-preview]",
        );

        const upload = root.querySelector(
          ".admin-upload",
        );

        let objectUrl = null;

        if (
          !input
          || !preview
        ) {
          return;
        }

        upload?.addEventListener(
          "keydown",
          (event) => {
            if (
              event.key !== "Enter"
              && event.key !== " "
            ) {
              return;
            }

            event.preventDefault();
            input.click();
          },
        );

        input.addEventListener(
          "change",
          () => {
            const file = (
              input.files?.[0]
            );

            if (!file) return;

            if (objectUrl) {
              URL.revokeObjectURL(
                objectUrl,
              );
            }

            objectUrl = (
              URL.createObjectURL(file)
            );

            preview.style.backgroundImage = (
              `url("${objectUrl}")`
            );

            preview.classList.add(
              "has-image",
            );
          },
        );

        window.addEventListener(
          "pagehide",
          () => {
            if (objectUrl) {
              URL.revokeObjectURL(
                objectUrl,
              );
            }
          },
          {
            once: true,
          },
        );
      });

    document
      .querySelectorAll(
        "[data-number-stepper]",
      )
      .forEach((root) => {
        const input = root.querySelector(
          "input[type='number']",
        );

        if (!input) return;

        root
          .querySelectorAll(
            "[data-step]",
          )
          .forEach((button) => {
            button.addEventListener(
              "click",
              () => {
                if (
                  button.dataset.step
                  === "up"
                ) {
                  input.stepUp();
                } else {
                  input.stepDown();
                }

                input.dispatchEvent(
                  new Event(
                    "change",
                    {
                      bubbles: true,
                    },
                  ),
                );

                input.focus({
                  preventScroll: true,
                });
              },
            );
          });
      });

    const slugify = (value) => (
      value
        .normalize("NFD")
        .replace(
          /[\u0300-\u036f]/g,
          "",
        )
        .toLowerCase()
        .replace(
          /[^a-z0-9]+/g,
          "-",
        )
        .replace(
          /^-+|-+$/g,
          "",
        )
        .slice(0, 190)
    );

    document
      .querySelectorAll(
        "[data-handle-field]",
      )
      .forEach((root) => {
        const input = (
          root.querySelector("input")
        );

        const status = (
          root.querySelector(
            "[data-handle-status]",
          )
        );

        const form = (
          root.closest("form")
        );

        const source = (
          form?.querySelector(
            "#display_name",
          )
          || form?.querySelector(
            "#name",
          )
        );

        if (
          !input
          || !status
        ) {
          return;
        }

        let manuallyEdited = Boolean(
          input.value.trim(),
        );

        let timer;

        const check = () => {
          const normalized = slugify(
            input.value,
          );

          input.value = normalized;

          if (!normalized) {
            status.textContent = (
              "O IDDUN vai gerar este "
              + "endereço automaticamente."
            );

            status.className = (
              "admin-handle-status"
            );

            return;
          }

          const params = (
            new URLSearchParams({
              type:
                root.dataset.handleType,
              value: normalized,
            })
          );

          if (
            root.dataset.currentId
          ) {
            params.set(
              "current_id",
              root.dataset.currentId,
            );
          }

          status.textContent = (
            "Verificando "
            + "disponibilidade…"
          );

          status.className = (
            "admin-handle-status "
            + "is-checking"
          );

          fetch(
            (
              "/admin/identificador/"
              + "disponibilidade?"
              + params.toString()
            ),
            {
              headers: {
                "X-Requested-With":
                  "XMLHttpRequest",
              },
            },
          )
            .then(
              (response) => (
                response.json()
              ),
            )
            .then((data) => {
              status.textContent = (
                data.available
                  ? (
                    `✓ iddun.com/`
                    + `${data.handle} `
                    + `está disponível`
                  )
                  : data.message
              );

              status.className = (
                "admin-handle-status "
                + (
                  data.available
                    ? "is-available"
                    : "is-unavailable"
                )
              );
            })
            .catch(() => {
              status.textContent = (
                "Não foi possível verificar "
                + "agora. O servidor valida "
                + "ao salvar."
              );

              status.className = (
                "admin-handle-status"
              );
            });
        };

        input.addEventListener(
          "input",
          () => {
            manuallyEdited = true;

            clearTimeout(timer);

            timer = setTimeout(
              check,
              300,
            );
          },
        );

        input.addEventListener(
          "blur",
          check,
        );

        source?.addEventListener(
          "input",
          () => {
            if (
              !manuallyEdited
              || !input.value.trim()
            ) {
              input.value = slugify(
                source.value,
              );

              clearTimeout(timer);

              timer = setTimeout(
                check,
                350,
              );
            }
          },
        );

        if (input.value) {
          check();
        }
      });
  },
);