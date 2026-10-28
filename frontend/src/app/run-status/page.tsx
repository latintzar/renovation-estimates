import { redirect } from "next/navigation";

/**
 * /run-status → /admin redirect
 * Old URL preserved for bookmarks.
 */
export default function RunStatusRedirect() {
  redirect("/admin");
}
