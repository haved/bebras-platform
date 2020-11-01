alter table `activity` change `type` `type` enum('load','attempt','submission','proxyload') CHARACTER SET utf8 NOT NULL;
