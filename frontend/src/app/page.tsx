import { redirect } from "next/navigation";

export default function Home() {
  // System design is the only vertical with a UI so far, so it is the app's
  // entry point rather than a dashboard that would sit mostly empty.
  redirect("/system-design");
}
