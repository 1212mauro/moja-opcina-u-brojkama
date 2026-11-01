import { getFormat } from "@/lib/format";
import {
  ACCESSIBILITY_STATEMENT_DATE,
  contactEmail,
  SITE_URL,
} from "@/lib/site";

/** The accessibility statement in English (E7); see hr-accessibility.tsx. */
export function AccessibilityText({ leadClass }: { leadClass: string }) {
  const date = getFormat("en").date(ACCESSIBILITY_STATEMENT_DATE);
  const email = contactEmail();
  return (
    <>
      <h1>Accessibility statement</h1>
      <p className={leadClass}>
        The project “My Municipality in Numbers” is committed to making its
        website accessible, in accordance with the Croatian Act on the
        Accessibility of Websites and Mobile Applications of Public Sector
        Bodies (Official Gazette 17/19).
      </p>
      <p>
        This accessibility statement applies to the website{" "}
        <a href={SITE_URL}>{SITE_URL}</a>.
      </p>

      <h2>Compliance status</h2>
      <p>
        This website is <strong>partially compliant</strong> with the Act and
        with EN 301 549 (WCAG 2.1, level AA), due to the non-compliances listed
        below.
      </p>

      <h2>Non-accessible content</h2>
      <h3>Non-compliance with the Act</h3>
      <ul>
        <li>
          We have not yet tested the site with screen-reader users (NVDA,
          VoiceOver). Until we do, we cannot guarantee that every chart and
          table makes sense when listened to.
        </li>
        <li>
          Payment categories, supplier names and contract subjects are shown as
          the towns and municipalities publish them, in Croatian, sometimes in
          capitals or with unexplained abbreviations.
        </li>
      </ul>
      <h3>Content outside the scope of the Act</h3>
      <ul>
        <li>
          Third-party maps and files we link to (OpenStreetMap, the source data
          of public bodies) are not under our control.
        </li>
      </ul>

      <h2>What we have done</h2>
      <ul>
        <li>
          Every chart has a sentence saying what it shows and a table with the
          same data.
        </li>
        <li>
          The map is never the only way: every town and municipality is also in
          a list, and every facility is also listed as text.
        </li>
        <li>
          The whole site works without JavaScript and with a keyboard, with a
          visible focus indicator and a link to skip to the content.
        </li>
        <li>
          Text colours have a contrast of at least 4.5:1 in light and dark mode.
        </li>
        <li>The site is also available in simple Croatian and in English.</li>
        <li>
          Every change to the site is checked automatically with axe-core.
        </li>
      </ul>

      <h2>Preparation of this statement</h2>
      <p>
        This statement was prepared on {date}, based on a self-assessment with
        automated testing (axe-core) and manual keyboard testing. It was last
        reviewed on {date}.
      </p>

      <h2>Feedback and contact information</h2>
      <p>
        If you notice anything on the site that is not accessible, or you need
        content in another format, contact us at{" "}
        <a href={`mailto:${email}`}>{email}</a>. We will reply within 15 days.
      </p>

      <h2>Enforcement procedure</h2>
      <p>
        If you are not satisfied with our reply, or we do not reply in time, you
        can contact the Croatian Information Commissioner, who monitors the
        application of the Act:{" "}
        <a href="https://www.pristupinfo.hr/" hrefLang="hr">
          www.pristupinfo.hr
        </a>
        .
      </p>
    </>
  );
}
