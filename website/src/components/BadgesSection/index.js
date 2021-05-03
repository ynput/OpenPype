import React from 'react';

import badges from './badges';
import styles from './styles.module.css';
import {StarButton} from "../index";

const Badge = props => (
  <a href={props.href} title={props.title}>
    <img src={props.src} alt={props.title}/>
  </a>
);

export default function BadgesSection() {
  const {upper: upperBadges} = badges;

  return (
    <div className={styles.badgesSection}>
      <div className={styles.upperBadges}>
        {upperBadges.map((badge, index) => (
          <Badge key={index} {...badge} />
        ))}
      </div>
    </div>
  );
};
