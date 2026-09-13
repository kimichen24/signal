import { redirect } from "next/navigation";

const isGitHubPages = process.env.DEPLOY_TARGET === "github-pages";

export default function RootPage() {
  if (isGitHubPages) {
    return (
      <html lang="zh-CN">
        <head>
          <meta httpEquiv="refresh" content="0;url=/signal/overview/" />
          <link rel="canonical" href="/signal/overview/" />
        </head>
        <body>
          <p>
            正在跳转至 <a href="/signal/overview/">总览</a>...
          </p>
        </body>
      </html>
    );
  }

  redirect("/overview");
}
