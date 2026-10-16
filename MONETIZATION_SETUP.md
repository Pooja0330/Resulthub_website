# GoResultHub monetization setup

This guide explains how to turn on legitimate revenue placements. No revenue is generated merely by adding the empty slots; the site must be approved by the provider and the real IDs must be configured.

## 1. Google AdSense (primary option)

1. Open Google AdSense and apply using the real https://goresulthub.com/ domain and an email you control.
2. Before applying, review the site for original, useful content, working pages, clear About/Contact/Privacy/Disclaimer pages, mobile usability, and broken or duplicate listings. An exam-link directory alone may not be enough to be approved; build genuinely useful, original exam-specific pages and avoid mass-generated thin pages.
3. Wait for Google's review. Do not put fake publisher IDs or another publisher's IDs in the code.
4. If approved, copy your publisher ID (ca-pub-...) and create ad units in AdSense. Copy the numeric ad-slot IDs.
5. Edit site/monetization.js:
   - Set adsenseClient to your own ca-pub-... ID.
   - Fill homeTop, homeMid, homeBottom, stateTop, and stateBottom with the matching numeric ad-slot IDs. Leave any placement blank if you do not want it.
6. Publish the changes. The ad containers remain hidden until valid IDs are present. Check the actual site and AdSense diagnostics after deployment.
7. After AdSense gives you the exact ads.txt line, create site/ads.txt with that exact line. Do not guess the publisher ID or publish a placeholder ads.txt.

Do not click your own ads, ask students to click ads, or place ads in a way that tricks visitors into clicking. Earnings depend on approval, eligible traffic, advertiser demand and policy compliance; they are not guaranteed.

## 2. Sponsored education resources / affiliate links

Contact legitimate education providers, test-prep companies, book sellers, and student tools about their official affiliate or sponsorship programs. Agree on terms before promoting anything. When you have a real partner URL, add an item to sponsoredResources in site/monetization.js, for example:

~~~js
{
  type: "Affiliate",
  title: "Partner name or resource",
  description: "Accurate description of what the student gets.",
  url: "https://your-real-approved-partner-link.example/"
}
~~~

Replace the example with a real approved URL. The website will label it as sponsored or affiliate and include a disclosure. Do not add fake offers, unsupported claims, or misleading countdowns. Do not use paid placements to imply that a partner is an official exam authority.

## 3. Direct sponsorships

Once the website has real traffic, offer clearly labelled sponsorship packages to relevant education brands. Keep a media kit with verified monthly users, page views, top exam categories, audience geography and Telegram subscribers. Never invent audience numbers. A sponsored card can be enabled through the same sponsoredResources list.

## 4. Measure results

Use Search Console to monitor indexing and organic search queries. If you later add Google Analytics 4 or another analytics service, configure it deliberately, update the privacy notice, and set up the consent controls required for the regions you serve before loading tracking code.

## 5. Telegram traffic

New automated Telegram alerts link to a search on GoResultHub only; the message no longer includes the direct official-source URL. Students can still reach the relevant official source from the listing on your website. The Telegram links include UTM tags so a configured analytics service can attribute visits to Telegram. Previously published Telegram messages cannot be edited by this code.

## Priority order

1. Fix broken sources and improve original exam-specific content.
2. Make sure About, Contact, Privacy, Terms and Disclaimer pages are accurate.
3. Apply for AdSense and wait for approval.
4. Configure real ad-unit IDs and ads.txt only when supplied by Google.
5. Add legitimate affiliate/sponsor partnerships and clearly disclose them.
