const React = require('react')
const moment = require('moment')
require('moment-timezone')

const pageTitle = 'Discord statistics'

const initialState = {
  userMessages: -1,
  botMessages: -1,
  messagesInLastWeek: -1,
  messagesInLastMonth: -1,
  dailyMessageCounts: [],
}

const formatDate = epochMs => moment(epochMs).tz('UTC').format('YYYY-MM-DD')

const formatNum = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ")

const dailyMessageCountTable = dailyMessageCounts =>
  <table>
    <thead>
      <tr>
          <td>Date</td>
          <td>User messages</td>
          <td>Bot messages</td>
      </tr>
    </thead>
    <tbody>
      {dailyMessageCounts.map(x =>
        <tr key={x.epoch}>
          <td>{formatDate(x.epoch)}</td>
          <td>{formatNum(x.user_count)}</td>
          <td>{formatNum(x.bot_count)}</td>
        </tr>
      )}
    </tbody>
  </table>

const renderPage = state =>
  <div>
    <h1>Discord statistics</h1>
    <p>Total messages {formatNum(state.userMessages + state.botMessages)}</p>
    <p>({formatNum(state.userMessages)} by users, {formatNum(state.botMessages)} by bots)</p>
    <p>Messages in last week {formatNum(state.messagesInLastWeek)}</p>
    <p>Messages in last month {formatNum(state.messagesInLastMonth)}</p>
    {dailyMessageCountTable(state.dailyMessageCounts)}
  </div>

module.exports = {
  pageTitle,
  initialState,
  renderPage,
}
