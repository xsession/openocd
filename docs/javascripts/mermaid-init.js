document$.subscribe(({ body }) => {
  if (typeof mermaid === "undefined") {
    return;
  }

  const dark = document.body.getAttribute("data-md-color-scheme") === "slate";
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: dark ? "dark" : "default",
  });
  mermaid.run({ nodes: body.querySelectorAll(".mermaid") });
});
