create table categories
(
	id integer not null
		primary key,
	title varchar(30) not null,
	description varchar(100) default '' not null,
	colour varchar(6) default '0f172a' not null
);

create table categoryAttributes
(
	id integer not null
		primary key,
	title varchar(25) not null,
	categoryID integer not null,
	datatype varchar(30) not null
);

create table conditions
(
	id integer not null
		primary key,
	title varchar(32) not null
);

create table listingAttributes
(
	id integer
		primary key,
	value varchar(50) not null,
	attributeID integer,
	listingID INTEGER not null
);

create table skuImages
(
	id TEXT not null
		primary key,
	skuID integer not null
);

create table subCategories
(
	id integer not null
		primary key,
	title varchar(32) not null,
	categoryID integer not null
);

create table userRatings
(
	id integer
		primary key,
	sourceUserID integer not null,
	rating integer not null,
	targetUserID integer not null
);

create table users
(
	id varchar(40) not null
		primary key,
	username varchar(40) not null,
	firstName varchar(40) not null,
	surname varchar(40) not null,
	passwordHash varchar not null,
	passwordSalt varchar not null,
	profilePictureURL varchar,
	bannerURL varchar,
	description varchar,
	streetAddress varchar,
	city varchar,
	region varchar,
	country varchar,
	joinedAt int(32) not null,
	emailAddress varchar(32) default '' not null
);

create table listings
(
	id varchar(40) not null
		primary key,
	title varchar(50) not null,
	description varchar(100),
	ownerID varchar(40) not null
		references users,
	views int(32) not null,
	rating float(10) not null,
	public bool default false,
	addedAt int(32) not null,
	subCategoryID integer default '' not null
);

create table listingEvents
(
	id integer not null
		primary key,
	eventType varchar(25) not null,
	userID integer not null
		references users,
	listingID integer not null
		references listings
);

create table skuTypes
(
	id integer not null
		primary key,
	title varchar(32) not null,
	listingID integer not null
		references listings
);

create table skuValues
(
	id integer not null
		primary key,
	title varchar(32) not null,
	skuTypeID integer not null
		references skuTypes,
	colour TEXT
);

create table skus
(
	id TEXT not null
		primary key,
	title TEXT not null,
	price TEXT not null,
	discount INTEGER default 0,
	conditionID integer default 0 not null
		references conditions,
	listingID integer not null
		references listings,
	stock INTEGER default '0' not null
);

create table skuOptions
(
	skuID TEXT not null
		references skus,
	valueID INTEGER not null
		references skuValues,
	primary key (skuID, valueID)
);

CREATE VIEW skuOptionsView AS
SELECT
    sk.id,
    sk.listingID AS listingId,
    sk.title,
    (
            SELECT json_group_object(
                st.title,  -- optionType
                sv.title  -- optionValue
            )
            FROM skuOptions so
            JOIN skuValues sv ON sv.id = so.valueID
            JOIN skuTypes st ON st.id = sv.skuTypeID
            WHERE so.skuID = sk.id
    ) AS options
FROM skus sk;

