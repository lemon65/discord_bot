const Promise = require('bluebird')
const pgp = require('pg-promise')({ promiseLib: Promise })

const connectionDetails = {
  host:     'localhost',
  port:     5432,
  database: process.env.DATABASE_NAME,
  user:     process.env.DATABASE_USERNAME,
  password: process.env.DATABASE_PASSWORD,
}

const db = pgp(connectionDetails)

const findUserMessageCount = () =>
  db.query('SELECT count(*)::numeric FROM message WHERE NOT bot').then(rows => Number(rows[0].count))

const findBotMessageCount = () =>
  db.query('SELECT count(*)::numeric FROM message WHERE bot').then(rows => Number(rows[0].count))

const messagesInLastNDays = days =>
  db.query(`
    SELECT sum(daily.count) AS count
    FROM (
      SELECT count(*)::numeric AS count
      FROM message
      GROUP BY ts::date
      ORDER BY ts::date DESC
      LIMIT ${Number(days)}
    ) AS daily
  `).then(rows => rows[0].count)

const findDailyMessageCounts = days =>
  db.query(`
    SELECT
      extract(epoch from ts::date) * 1000 as epoch,
      sum(case bot when true then 1 else 0 end) as bot_count,
      sum(case bot when false then 1 else 0 end) as user_count
    FROM message
    GROUP BY ts::date
    ORDER BY ts::date DESC
    LIMIT ${Number(days)}
  `)

module.exports = {
  findUserMessageCount,
  findBotMessageCount,
  messagesInLastNDays,
  findDailyMessageCounts,
}
