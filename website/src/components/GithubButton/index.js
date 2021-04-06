import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

export function StarButton() {
  const context = useDocusaurusContext();
  const {siteConfig = {}} = context;

  return <a
    className="github-button"
    href={siteConfig.customFields.mainRepoUrl}
    title="See this project on GitHub"
    data-icon="octicon-star"
    data-show-count="true"
    data-count-href={`/${siteConfig.organizationName}/${siteConfig.projectName}/stargazers`}
    data-count-aria-label="# stargazers on GitHub"
    aria-label="Star this project on GitHub">
    T-Regx
  </a>;
}

export function SponsorButton() {
  return <div style={{height: '32px'}}>
    <iframe
      src=""
      title="Sponsor"
      height="35"
      width="116"
      style={{"border": 0}}/>
  </div>;
}
