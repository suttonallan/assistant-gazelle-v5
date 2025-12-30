# Schéma GraphQL Gazelle - Documentation Complète

**Date de génération:** 2025-12-30 17:18:38

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Types Query](#types-query)
3. [Types Mutation](#types-mutation)
4. [Types Objets](#types-objets)
5. [Types Input](#types-input)
6. [Types Enum](#types-enum)

---

## Vue d'ensemble

- **Query Type:** `PrivateQuery`
- **Mutation Type:** `PrivateMutation`
- **Total Types:** 720

---

## Types Query

### PrivateQuery

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allAccountingTaxMappings` | `[PrivateRemoteAccountingTaxMapping!]!` | type: RemoteAccountingType! | - |
| `allAddressDisplayTemplates` | `[AddressDisplayTemplate!]!` | - | - |
| `allAuthorizedIntegrations` | `[PrivateAuthorizedIntegration!]!` | - | This is a list of all the applications that have been authorized by users to access this Gazelle account.  This is only available to API requests authenticated with full admin access. |
| `allAvailability` | `[PrivateAvailability!]!` | userId: [String!]!, startOn: CoreDate!, endOn: CoreDate! | - |
| `allCallCenterItems` | `PrivateCallCenterItemConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllCallCenterItemsFilter, sortBy: [CallCenterItemSort!] | - |
| `allClientTags` | `[String!]!` | - | This is a list of all the unique client tags for the company. |
| `allClients` | `PrivateClientConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllClientsFilter, sortBy: [ClientSort!] | - |
| `allCurrencies` | `[CoreCurrency!]!` | - | A list of all the currencies that Gazelle supports along with formatting and display information about each.  To know which one is being used by this company, have a look at company{settings{localization{defaultCurrency}} |
| `allErrorLogs` | `PrivateErrorLogConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllErrorLogsFilter, sortBy: [ErrorLogSort!] | - |
| `allEstimateChecklists` | `[PrivateEstimateChecklist!]!` | - | - |
| `allEstimateTags` | `[String!]!` | - | This is a list of all the unique estimate tags for the company. |
| `allEstimates` | `PrivateEstimateConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllEstimatesFilter, sortBy: [EstimateSort!] | - |
| `allEventCancelNotices` | `PrivateEventCancelNoticeConnection!` | after: String, before: String, first: Int, last: Int, status: [EventCancelNoticeStatus!] | - |
| `allEventReservations` | `[PrivateEventReservation!]!` | filters: PrivateAllEventReservationsFilter, sortBy: [EventReservationSort!] | - |
| `allEventReservationsBatched` | `PrivateEventReservationConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllEventReservationsFilter, sortBy: [EventReservationSort!] | - |
| `allEvents` | `[PrivateEvent!]!` | filters: PrivateAllEventsFilter, sortBy: [EventSort!] | - |
| `allEventsBatched` | `PrivateEventConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllEventsFilter, sortBy: [EventSort!] | - |
| `allGazelleReferrals` | `[PrivateGazelleReferral!]!` | - | - |
| `allInvoiceTags` | `[String!]!` | - | This is a list of all the unique invoice tags for the company. |
| `allInvoices` | `PrivateInvoiceConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllInvoicesFilter, sortBy: [InvoiceSort!] | - |
| `allLifecycles` | `PrivateLifecycleConnection!` | after: String, before: String, first: Int, last: Int, search: String, sortBy: [LifecycleSort!] | - |
| `allLocalizations` | `[CoreLocalization!]!` | - | Localizations describe which translation to use, and how to format numbers, dates, and currencies.  This is a list of all localizations that the company has defined. You most likely don't want to use this, but instead have a look at company{settings{localizations{defaultUserLocalization defaultClientLocalization}}} and user{defaultUserLocalization defaultClientLocalization} and client{defaultClientLocalization} |
| `allLocations` | `[PrivateLocation!]!` | userId: [String!] | - |
| `allMailchimpAudiences` | `[PrivateMailchimpAudience!]!` | - | - |
| `allMasterServiceGroups` | `[PrivateMasterServiceGroup!]!` | - | - |
| `allMasterServiceItems` | `[PrivateMasterServiceItem!]!` | - | - |
| `allMessages` | `PrivateTimelineEntryConnection!` | after: String, before: String, first: Int, last: Int, types: [TimelineEntryType!], search: String | - |
| `allPastAndPresentTaxes` | `[PrivateTax!]!` | - | - |
| `allPianoTags` | `[String!]!` | - | This is a list of all the unique piano tags for the company. |
| `allPianos` | `PrivatePianoConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllPianosFilter, sortBy: [PianoSort!] | - |
| `allQuickbooksAccountMappings` | `[PrivateQuickbooksAccountMapping!]!` | - | - |
| `allQuickbooksAccounts` | `[PrivateRemoteQuickbooksAccount!]!` | - | - |
| `allQuickbooksSyncBatches` | `PrivateQuickbooksSyncBatchConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allRecommendations` | `[PrivateRecommendation!]!` | includeArchived: Boolean | - |
| `allRemoteAccountingTaxes` | `[PrivateRemoteTax!]!` | type: RemoteAccountingType! | - |
| `allRemoteCalendarIntegrations` | `[PrivateRemoteCalendarIntegration!]!` | - | - |
| `allScheduledMessageTemplates` | `PrivateScheduledMessageTemplateConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allScheduledMessages` | `PrivateScheduledMessageConnection!` | after: String, before: String, first: Int, last: Int, clientId: String | - |
| `allSchedulerAvailabilities` | `[PrivateSchedulerAvailability!]!` | userId: String, startOn: CoreDate, endOn: CoreDate | This is a list of all the availabilities for a user.  If no userId is provided, this will return all scheduler availabilities for the user authenticated to this query. |
| `allSchedulerServiceAreas` | `[PrivateSchedulerServiceArea!]!` | userId: String, allActiveUsers: Boolean | This is a list of all the service areas for a user.  If no userId is provided, this will return all scheduler service areas for the user authenticated to this query. |
| `allSelfConfirmedAppointments` | `PrivateEventConnection!` | after: String, before: String, first: Int, last: Int, confirmedOnGet: CoreDate, confirmedOnLet: CoreDate, sortBy: [SelfConfirmedAppointmentSort!] | - |
| `allSentOrScheduledMessages` | `PrivateSentOrScheduledMessageConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllSentOrScheduledMessagesFilter, sortBy: [SentOrScheduledMessageSort!] | - |
| `allServiceLibraryGroups` | `[PrivateServiceLibraryGroup!]!` | - | - |
| `allServiceLibraryItems` | `PrivateServiceLibraryItemConnection!` | after: String, before: String, first: Int, last: Int, name: I18nString | - |
| `allSkipStripePayouts` | `[PrivateSkipStripePayout!]!` | - | - |
| `allSupportedLocales` | `[CoreSupportedLocaleInfo!]!` | - | This is a static list of all the locales that are supported by default.  It contains a list of languages and date, time, number formatters for reach locale.  These can be customized through the Localization models, but this is a static list of system defaults that are supported. |
| `allSupportedLocalesCountryNames` | `[CountryNamesLocalization!]!` | - | This is a static list of country names localized in all supported locales. |
| `allSystemNotifications` | `PrivateSystemNotificationConnection!` | after: String, before: String, first: Int, last: Int, since: CoreDate, alertTypes: [SystemNotificationAlertType!], types: [SystemNotificationType!], excludeClientRelatedNotifications: Boolean, sortBy: [SystemNotificationSort!] | - |
| `allTaxes` | `[PrivateTax!]!` | - | - |
| `allTimelineEntries` | `PrivateTimelineEntryConnection!` | after: String, before: String, first: Int, last: Int, clientId: String, pianoId: String, invoiceId: String, estimateId: String, types: [TimelineEntryType!], search: String, occurredAtGet: CoreDateTime | - |
| `allUncompletedAppointments` | `PrivateEventConnection!` | after: String, before: String, first: Int, last: Int, filters: PrivateAllUncompletedAppointmentsFilter, sortBy: [EventSort!] | - |
| `allUsers` | `[PrivateUser!]!` | - | - |
| `badgeCount` | `PrivateBadgeCount!` | - | - |
| `bulkAction` | `PrivateBulkAction` | id: String! | - |
| `bulkChangeClientStatusConfirmationMessages` | `[String!]!` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateChangeClientStatusInput! | This returns an array of confirmation messages that should be displayed before executing the createBulkChangeClientStatusJob mutation. |
| `bulkMarkAppointmentsCompleteConfirmationMessages` | `[String!]!` | filters: PrivateAllUncompletedAppointmentsFilter, selection: PrivateSelectionInput! | This returns an array of confirmation messages that should be displayed before executing the createBulkMarkAppointmentsCompleteJob mutation. |
| `bulkPauseClientsConfirmationMessages` | `[String!]!` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateBulkPauseClientsInput! | This returns an array of confirmation messages that should be displayed before executing the createBulkPauseClientsJob mutation. |
| `bulkReminderReassignmentConfirmationMessages` | `[String!]!` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkReminderReassignmentInput! | This returns an array of confirmation messages that should be displayed before executing the createBulkReminderReassignmentJob mutation. |
| `callCenterItem` | `PrivateCallCenterItem` | referenceType: CallCenterReferenceType!, referenceId: String! | - |
| `client` | `PrivateClient` | clientId: String, id: String | - |
| `company` | `PrivateCompany` | - | - |
| `companyEmailTemplate` | `String!` | name: CompanyEmailTemplateType! | - |
| `contact` | `PrivateContact` | id: String! | - |
| `dashboardMetrics` | `PrivateDashboardMetrics!` | - | - |
| `driveTimes` | `PrivateDriveTimes!` | referer: String, sourceAddress: String, destinationAddress: String, sourceLat: Float, sourceLng: Float, destinationLat: Float, destinationLng: Float, departureTime: CoreDateTime, timezone: String | - |
| `email` | `PrivateEmail` | emailId: String! | - |
| `estimate` | `PrivateEstimate` | id: String! | - |
| `estimateChecklist` | `PrivateEstimateChecklist` | id: String! | - |
| `estimateChecklistGroup` | `PrivateEstimateChecklistGroup` | id: String! | - |
| `estimateChecklistItem` | `PrivateEstimateChecklistItem` | id: String! | - |
| `estimateTier` | `PrivateEstimateTier` | id: String! | - |
| `estimateTierGroup` | `PrivateEstimateTierGroup` | id: String! | - |
| `estimateTierItem` | `PrivateEstimateTierItem` | id: String! | - |
| `event` | `PrivateEvent` | eventId: String! | - |
| `eventReservation` | `PrivateEventReservation` | id: String! | - |
| `gazelleReferrerName` | `String` | referralToken: String! | - |
| `globalConfig` | `PrivateGlobalConfig!` | - | - |
| `invoice` | `PrivateInvoice` | id: String! | - |
| `invoicePayment` | `PrivateInvoicePayment` | id: String! | - |
| `legalContracts` | `[PrivateLegalContract!]!` | - | This will return a list of all the legal contracts (signed and unsigned) and DPAs for your account's locale. |
| `lifecycleContactLog` | `PrivateLifecycleContactLog` | id: String! | - |
| `mailchimpIntegration` | `PrivateMailchimpIntegration!` | - | - |
| `nextLifecycleMessages` | `PrivateNextLifecycleMessageConnection!` | after: String, before: String, first: Int, last: Int, clientId: String! | - |
| `onboarding` | `PrivateOnboarding!` | - | - |
| `piano` | `PrivatePiano` | pianoId: String, id: String | - |
| `pianoMeasurement` | `PrivatePianoMeasurement` | id: String! | - |
| `previewGazelleReferralEmail` | `String!` | name: String!, email: String! | - |
| `previewSharedCalendarInvitationEmail` | `PrivateTemplatePreview` | email: String!, userId: String | - |
| `previewSharedCalendarRequestEmail` | `PrivateTemplatePreview` | name: String!, email: String! | - |
| `pricing` | `PrivatePricing!` | affiliateCode: String | - |
| `pricingV4TransitionPhase` | `Int!` | - | While we are rolling out our Jakklops pricing, this tells which phase of the rollout we are currently in. |
| `quickbooksSyncBatch` | `PrivateQuickbooksSyncBatch` | id: String! | - |
| `quickbooksSyncCurrentlyRunningBatch` | `PrivateQuickbooksSyncBatch` | - | - |
| `remoteAccountingIntegrations` | `PrivateRemoteAccountingIntegration!` | - | - |
| `remoteCalendar` | `PrivateRemoteCalendar` | id: String! | - |
| `remoteCalendarIntegration` | `PrivateRemoteCalendarIntegration` | id: String! | - |
| `renameTagImpacts` | `PrivateRenameTagImpacts!` | originalTag: String!, newTag: String!, modelType: PrivateTagModelType! | - |
| `scheduledMessage` | `PrivateScheduledMessage` | id: String, scheduledMessageId: String | - |
| `scheduledMessageTemplate` | `PrivateScheduledMessageTemplate` | scheduledMessageTemplateId: String! | - |
| `schedulerAvailability` | `PrivateSchedulerAvailability` | id: String!, userId: String | - |
| `schedulerV2SearchProgress` | `Int!` | technicianSearchSignatures: [String!]! | - |
| `schedulerV2SearchResults` | `PrivateSchedulerV2SearchResultsWrapper!` | technicianSearchSignatures: [String!]! | - |
| `sharedCalendars` | `[PrivateSharedCalendar!]!` | userId: String | - |
| `smsMessage` | `PrivateSmsMessage` | id: String! | - |
| `stripePaymentProcessing` | `PrivateStripePaymentProcessing!` | - | - |
| `stripePrices` | `[CoreStripePrice!]!` | - | This is a static list of all the countries that are enabled for Stripe payments, and the pricing for supported payment methods in each country. |
| `supportedCountries` | `[CoreCountryInfo!]!` | - | - |
| `templatePreview` | `PrivateTemplatePreview!` | subject: String, message: String!, messageType: String!, messageTemplateType: String | - |
| `travelTimes` | `PrivateTravelTimes!` | travelMode: SchedulerTravelMode!, referer: String, sourceAddress: String, destinationAddress: String, sourceLat: Float, sourceLng: Float, destinationLat: Float, destinationLng: Float, departureTime: CoreDateTime, timezone: String | - |
| `upcomingLifecycleReminders` | `PrivateUpcomingLifecycleReminder!` | - | Aggregations of the upcoming Email and SMS reminders going out in the next 72 hours. |
| `user` | `PrivateUser` | - | - |

---

## Types Mutation

### PrivateMutation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addFeatureTrialToSubscription` | `AddFeatureTrialToSubscriptionPayload` | feature: PrivateJakklopsPricingFeatureType! | - |
| `addInvoicePayment` | `AddInvoicePaymentPayload` | invoiceId: String!, paymentAmount: Int!, paymentType: InvoicePaymentType, paymentNotes: String, paymentTipAmount: Int, paymentPaidAt: CoreDateTime | - |
| `addressComponents` | `AddressComponentsPayload` | addressLine: String!, referer: String | Takes a 1-line address and extracts it into its component parts. |
| `approveEventReservation` | `ApproveEventReservationPayload` | id: String!, input: PrivateApproveEventReservationInput! | - |
| `cancelEvent` | `CancelEventPayload` | eventId: String! | - |
| `cancelPendingCancellation` | `CancelPendingBillingPlanCancellationPayload` | - | - |
| `cancelPlan` | `CancelBillingPlanPayload` | input: PrivateCancelBillingPlanInput | - |
| `changeEventReservationToPending` | `ChangeEventReservationToPendingPayload` | id: String! | - |
| `changeMasterServiceListPrices` | `ChangeMasterServiceListPricesPayload` | input: ChangeMasterServiceListPricesInput! | - |
| `changeOwnPassword` | `ChangeOwnPasswordPayload` | currentPassword: String!, newPassword: String!, newPasswordConfirmation: String! | - |
| `changePlan` | `ChangeBillingPlanPayload` | id: String!, featureTrials: [PrivateJakklopsPricingFeatureType!], paymentMethodId: String | - |
| `chooseMailchimpAudience` | `ChooseMailchimpAudiencePayload` | mailchimpAudienceId: String! | - |
| `completeEvent` | `CompleteEventPayload` | eventId: String!, input: PrivateCompleteEventInput | - |
| `completePasswordReset` | `CompletePasswordResetPayload` | token: String!, password: String! | - |
| `confirmEvent` | `ConfirmEventPayload` | id: String!, input: PrivateConfirmEventInput | - |
| `createAndRunQuickbooksSyncBatch` | `CreateAndRunQuickbooksSyncBatchPayload` | invoiceInput: [PrivateQuickbooksSyncInvoiceInput!]!, pullPayments: Boolean, syncStripePayouts: Boolean | - |
| `createBulkAddClientTagJob` | `CreateBulkAddClientTagJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkAddClientTagJobInput! | - |
| `createBulkAddEstimateTagJob` | `CreateBulkAddEstimateTagJobPayload` | filters: PrivateAllEstimatesFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkAddEstimateTagJobInput! | - |
| `createBulkAddInvoiceTagJob` | `CreateBulkAddInvoiceTagJobPayload` | filters: PrivateAllInvoicesFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkAddInvoiceTagJobInput! | - |
| `createBulkAddPianoTagJob` | `CreateBulkAddPianoTagJobPayload` | filters: PrivateAllPianosFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkAddPianoTagJobInput! | - |
| `createBulkArchiveEstimateJob` | `CreateBulkArchiveEstimateJobPayload` | filters: PrivateAllEstimatesFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkArchiveEstimateJobInput! | - |
| `createBulkArchiveInvoiceJob` | `CreateBulkArchiveInvoiceJobPayload` | filters: PrivateAllInvoicesFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkArchiveInvoiceJobInput! | - |
| `createBulkChangeClientStatusJob` | `CreateBulkChangeClientStatusJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateChangeClientStatusInput! | - |
| `createBulkChangePianoStatusJob` | `CreateBulkChangePianoStatusJobPayload` | filters: PrivateAllPianosFilter, selection: PrivateSelectionInput!, input: PrivateChangePianoStatusInput! | - |
| `createBulkExportClientsJob` | `CreateBulkExportClientsJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput! | - |
| `createBulkExportClientsToMailchimpJob` | `CreateBulkExportClientsToMailchimpJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkExportClientsToMailchimpInput | - |
| `createBulkExportEventsJob` | `CreateBulkExportEventsJobPayload` | filters: PrivateAllEventsFilter, selection: PrivateSelectionInput! | - |
| `createBulkExportInvoicesJob` | `CreateBulkExportInvoicesJobPayload` | filters: PrivateAllInvoicesFilter, selection: PrivateSelectionInput! | - |
| `createBulkExportPianosJob` | `CreateBulkExportPianosJobPayload` | filters: PrivateAllPianosFilter, selection: PrivateSelectionInput! | - |
| `createBulkMarkAppointmentsCompleteJob` | `CreateBulkMarkAppointmentsCompleteJobPayload` | input: PrivateCreateBulkMarkAppointmentsCompleteJobInput!, selection: PrivateSelectionInput!, filters: PrivateAllEventsFilter | - |
| `createBulkPauseClientsJob` | `CreateBulkPauseClientsJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateBulkPauseClientsInput! | - |
| `createBulkRecordCallCenterActionJob` | `CreateBulkRecordCallCenterActionJobPayload` | filters: PrivateAllCallCenterItemsFilter, selection: PrivateSelectionInput!, input: PrivateRecordCallCenterActionInput! | - |
| `createBulkReminderReassignmentJob` | `CreateBulkReminderReassignmentJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkReminderReassignmentInput! | - |
| `createBulkRemoveClientTagJob` | `CreateBulkRemoveClientTagJobPayload` | filters: PrivateAllClientsFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkRemoveClientTagJobInput! | - |
| `createBulkRemoveEstimateTagJob` | `CreateBulkRemoveEstimateTagJobPayload` | filters: PrivateAllEstimatesFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkRemoveEstimateTagJobInput! | - |
| `createBulkRemoveInvoiceTagJob` | `CreateBulkRemoveInvoiceTagJobPayload` | filters: PrivateAllInvoicesFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkRemoveInvoiceTagJobInput! | - |
| `createBulkRemovePianoTagJob` | `CreateBulkRemovePianoTagJobPayload` | filters: PrivateAllPianosFilter, selection: PrivateSelectionInput!, input: PrivateCreateBulkRemovePianoTagJobInput! | - |
| `createClient` | `CreateClientPayload` | input: PrivateClientInput!, id: String | - |
| `createClientLog` | `CreateClientLogPayload` | clientId: String!, pianoId: String, input: PrivateClientLogInput! | - |
| `createContact` | `CreateContactPayload` | clientId: String!, input: PrivateContactInput! | - |
| `createContactAddress` | `CreateContactAddressPayload` | contactId: String!, input: PrivateContactAddressInput!, replaceExistingType: Boolean | - |
| `createContactEmail` | `CreateContactEmailPayload` | contactId: String!, input: PrivateContactEmailInput! | - |
| `createContactLocation` | `CreateContactLocationPayload` | contactId: String!, input: PrivateContactLocationInput!, replaceExistingType: Boolean | - |
| `createContactPhone` | `CreateContactPhonePayload` | contactId: String!, input: PrivateContactPhoneInput! | - |
| `createEstimate` | `CreateEstimatePayload` | input: PrivateCreateEstimateInput! | - |
| `createEstimateChecklist` | `CreateEstimateChecklistPayload` | input: PrivateEstimateChecklistInput! | - |
| `createEstimateChecklistGroup` | `CreateEstimateChecklistGroupPayload` | input: PrivateEstimateChecklistGroupInput!, estimateChecklistId: String! | - |
| `createEstimateChecklistItem` | `CreateEstimateChecklistItemPayload` | input: PrivateEstimateChecklistItemInput!, estimateChecklistId: String!, estimateChecklistGroupId: String, masterServiceItemId: String | - |
| `createEvent` | `CreateEventPayload` | input: PrivateEventInput! | - |
| `createFeatureAccessRequestNotice` | `CreateFeatureAccessRequestNoticePayload` | quickbooksOnlineRequest: Boolean | This will add the current company to a list of people who want access to this feature. |
| `createFeatureRequestNotice` | `CreateFeatureRequestNoticePayload` | quickbooksOnlineRequest: Boolean | - |
| `createGazelleMailchimpAudience` | `CreateGazelleMailchimpAudiencePayload` | - | - |
| `createInvoice` | `CreateInvoicePayload` | input: PrivateCreateInvoiceInput!, id: String | - |
| `createLocalization` | `CreateLocalizationPayload` | input: PrivateLocalizationInput! | - |
| `createMasterServiceGroup` | `CreateMasterServiceGroupPayload` | input: PrivateMasterServiceGroupInput! | - |
| `createMasterServiceItem` | `CreateMasterServiceItemPayload` | input: PrivateMasterServiceItemInput! | - |
| `createPiano` | `CreatePianoPayload` | input: PrivatePianoInput! | - |
| `createPianoMeasurement` | `CreatePianoMeasurementPayload` | input: PrivatePianoMeasurementInput! | - |
| `createPianoPhoto` | `CreatePianoPhotoPayload` | input: PrivatePianoPhotoInput! | - |
| `createQuickbooksAccountMapping` | `CreateQuickbooksAccountMappingPayload` | input: PrivateQuickbooksAccountMappingInput! | - |
| `createRecommendation` | `CreateRecommendationPayload` | input: PrivateRecommendationInput! | - |
| `createRemoteAccountingTaxMapping` | `CreateRemoteAccountingTaxMappingPayload` | input: PrivateRemoteAccountingTaxMappingInput! | - |
| `createRemoteCalendar` | `CreateRemoteCalendarPayload` | remoteCalendarIntegrationId: String!, input: PrivateRemoteCalendarInput! | - |
| `createRemoteCalendarIntegration` | `CreateRemoteCalendarIntegrationPayload` | input: PrivateRemoteCalendarIntegrationInput! | - |
| `createScheduledMessage` | `CreateScheduledMessagePayload` | input: PrivateScheduledMessageInput! | - |
| `createScheduledMessageTemplate` | `CreateScheduledMessageTemplatePayload` | input: PrivateScheduledMessageTemplateInput! | - |
| `createSchedulerAvailability` | `CreateSchedulerAvailabilityPayload` | userId: String, input: PrivateSchedulerAvailabilityInput! | - |
| `createSchedulerServiceArea` | `CreateSchedulerServiceAreaPayload` | userId: String!, input: PrivateSchedulerServiceAreaInput! | - |
| `createSharedCalendarViaAuth` | `CreateSharedCalendarViaAuthPayload` | errorReferenceId: String, showEventDetails: Boolean!, includeClientPianoDetails: Boolean!, eventTypesToShare: [EventType!]!, username: String!, password: String! | - |
| `createSharedCalendarViaToken` | `CreateSharedCalendarViaTokenPayload` | errorReferenceId: String, showEventDetails: Boolean!, includeClientPianoDetails: Boolean!, eventTypesToShare: [EventType!]!, sharedToEmailAddress: String!, userId: String! | - |
| `createSkipStripePayout` | `CreateSkipStripePayoutPayload` | stripePayoutId: String!, reason: String | - |
| `createStripeCheckoutSession` | `CreateStripeCheckoutSessionPayload` | invoiceId: String!, receiptEmail: String, receiptContactEmailId: String, receiptAltBilling: Boolean, totalPaymentAmount: Int!, tipAmount: Int, notes: String, stripeRedirectUrl: String | Creates a checkout session with Stripe. |
| `createStripeSetupIntent` | `CreateStripeSetupIntentPayload` | cardOnly: Boolean | - |
| `createTax` | `CreateTaxPayload` | name: String!, rate: Int!, default: Boolean | - |
| `createUser` | `CreateUserPayload` | input: PrivateCreateUserInput! | - |
| `declineEventReservation` | `DeclineEventReservationPayload` | id: String!, input: PrivateDeclineEventReservationInput! | - |
| `deleteClient` | `DeleteClientPayload` | id: String! | - |
| `deleteClientLog` | `DeleteClientLogPayload` | id: String! | - |
| `deleteContact` | `DeleteContactPayload` | id: String! | - |
| `deleteContactAddress` | `DeleteContactAddressPayload` | id: String! | - |
| `deleteContactEmail` | `DeleteContactEmailPayload` | id: String! | - |
| `deleteContactLocation` | `DeleteContactLocationPayload` | id: String! | - |
| `deleteContactPhone` | `DeleteContactPhonePayload` | id: String! | - |
| `deleteEstimate` | `DeleteEstimatePayload` | id: String! | - |
| `deleteEstimateChecklist` | `DeleteEstimateChecklistPayload` | id: String! | - |
| `deleteEstimateChecklistGroup` | `DeleteEstimateChecklistGroupPayload` | id: String! | - |
| `deleteEstimateChecklistItem` | `DeleteEstimateChecklistItemPayload` | id: String! | - |
| `deleteEvent` | `DeleteEventPayload` | id: String!, recurrenceChangeType: EventRecurrenceChangeType | - |
| `deleteEventReservation` | `DeleteEventReservationPayload` | id: String!, clientId: String | - |
| `deleteInvoicePayment` | `DeleteInvoicePaymentPayload` | invoiceId: String!, paymentId: String! | - |
| `deleteLocalization` | `DeleteLocalizationPayload` | id: String! | - |
| `deleteMasterServiceGroup` | `DeleteMasterServiceGroupPayload` | id: String! | - |
| `deleteMasterServiceItem` | `DeleteMasterServiceItemPayload` | id: String! | - |
| `deletePiano` | `DeletePianoPayload` | id: String! | - |
| `deletePianoMeasurement` | `DeletePianoMeasurementPayload` | id: String! | - |
| `deletePianoPhoto` | `DeletePianoPhotoPayload` | id: String! | - |
| `deletePushToken` | `DeletePushTokenPayload` | pushToken: String! | - |
| `deleteQuickbooksAccountMapping` | `DeleteQuickbooksAccountMappingPayload` | id: String! | - |
| `deleteRecommendation` | `DeleteRecommendationPayload` | id: String! | - |
| `deleteRemoteAccountingTaxMapping` | `DeleteRemoteAccountingTaxMappingPayload` | id: String! | - |
| `deleteRemoteCalendar` | `DeleteRemoteCalendarPayload` | id: String! | - |
| `deleteRemoteCalendarIntegration` | `DeleteRemoteCalendarIntegrationPayload` | id: String! | - |
| `deleteScheduledMessage` | `DeleteScheduledMessagePayload` | id: String!, deleteScheduledMessages: Boolean | - |
| `deleteScheduledMessageTemplate` | `DeleteScheduledMessageTemplatePayload` | id: String!, deleteScheduledMessages: Boolean | - |
| `deleteSchedulerAvailabilities` | `DeleteSchedulerAvailabilitiesPayload` | ids: [String!]! | - |
| `deleteSchedulerAvailability` | `DeleteSchedulerAvailabilityPayload` | id: String! | - |
| `deleteSchedulerServiceArea` | `DeleteSchedulerServiceAreaPayload` | id: String! | - |
| `deleteSchedulerV2Settings` | `DeleteSchedulerV2SettingsPayload` | userId: String | This mutation will only exist during the transition period between scheduler v1 and v2.  It will be removed once all customers have migrated to v2 and support for v1 has been removed. |
| `deleteSharedCalendar` | `DeleteSharedCalendarPayload` | id: String! | - |
| `deleteSkipStripePayout` | `DeleteSkipStripePayoutPayload` | stripePayoutId: String! | - |
| `deleteTag` | `DeleteTagPayload` | input: PrivateDeleteTagInput! | This mutation will remove the tag from all records. |
| `deleteTax` | `DeleteTaxPayload` | id: String! | - |
| `disconnectMailchimp` | `DisconnectMailchimpPayload` | - | - |
| `disconnectQuickbooksOnline` | `DisconnectQuickbooksOnlinePayload` | - | - |
| `disconnectStripePayments` | `DisconnectStripePaymentsPayload` | - | - |
| `dismissAllErrorLogs` | `DismissAllErrorLogsPayload` | - | - |
| `dismissAllEventCancelNotices` | `DismissAllEventCancelNoticesPayload` | - | - |
| `dismissErrorLog` | `DismissErrorLogPayload` | id: String! | - |
| `dismissSystemNotification` | `DismissSystemNotificationPayload` | id: String!, dismissForEveryone: Boolean | - |
| `geocode` | `GeocodePayload` | addressLine: String!, referer: String | - |
| `importServiceLibraryItems` | `ImportServiceLibraryItemsPayload` | groups: [ImportServiceLibraryItemsInput!]! | - |
| `initiatePasswordReset` | `InitiatePasswordResetPayload` | email: String! | - |
| `mergeClients` | `MergeClientsPayload` | input: PrivateMergeClientsInput! | - |
| `mergePianos` | `MergePianosPayload` | input: PrivateMergePianosInput! | - |
| `migrateSchedulerV2Settings` | `MigrateSchedulerV2SettingsPayload` | userId: String, destructive: Boolean, onlyDeleteSettings: Boolean | This mutation will only exist during the transition period between scheduler v1 and v2.  It will be removed once all customers have migrated to v2 and support for v1 has been removed. |
| `recordCallCenterContact` | `RecordCallCenterContactPayload` | referenceType: CallCenterReferenceType!, referenceId: String!, contactKind: CallCenterContactKind!, notes: String | Record contact for either a scheduled message or lifecycle contact log |
| `removeCompanyLogo` | `RemoveCompanyLogoPayload` | - | - |
| `removeFeatureTrialFromSubscription` | `RemoveFeatureTrialFromSubscriptionPayload` | feature: PrivateJakklopsPricingFeatureType! | - |
| `renameTag` | `RenameTagPayload` | input: PrivateRenameTagInput! | This mutation will update all references to the old tag name to the new tag name. |
| `resendSharedCalendarToken` | `ResendSharedCalendarTokenPayload` | sharedCalendarId: String! | - |
| `revokeAuthorizedIntegration` | `RevokeAuthorizedIntegrationPayload` | id: String!, userId: String! | - |
| `schedulerV2RecordSelectedSlot` | `SchedulerV2RecordSelectedSlotPayload` | searchId: String!, technicianId: String!, startsAt: CoreDateTime! | - |
| `schedulerV2Search` | `SchedulerV2SearchPayload` | searchParams: PrivateSchedulerV2SearchInput! | - |
| `sendCalendarShareInstructions` | `SendCalendarShareInstructionsPayload` | email: String!, name: String! | - |
| `sendEstimateEmail` | `SendEstimateEmailPayload` | estimateId: String!, sendToContactEmailIds: [String!], attachPdf: Boolean, emailSubject: String, emailMessage: String | - |
| `sendInvoiceEmail` | `SendInvoiceEmailPayload` | invoiceId: String!, sendToAltBilling: Boolean, sendToContactEmailIds: [String!], attachPdf: Boolean, newInvoiceStatus: InvoiceStatus, emailSubject: String, emailMessage: String | - |
| `sendReferral` | `SendReferralPayload` | name: String!, email: String!, errorReferenceId: String | - |
| `sendSchedulerV2Feedback` | `SendSchedulerV2FeedbackPayload` | searchId: String!, reservationId: String, feedback: String! | This mutation will only exist during the transition period between scheduler v1 and v2.  It will be removed once all customers have migrated to v2 and support for v1 has been removed. |
| `setCanadianZeroPercentTaxRate` | `SetCanadianZeroPercentTaxRatePayload` | externalTaxId: String! | - |
| `signLegalContract` | `SignLegalContractPayload` | legalContractId: String! | - |
| `signup` | `SignupPayload` | input: PrivateSignupInput! | - |
| `startFeatureTrial` | `StartFeatureTrialPayload` | feature: PrivateJakklopsPricingFeatureType! | - |
| `syncRemoteCalendar` | `SyncRemoteCalendarPayload` | id: String! | - |
| `toggleSharedCalendar` | `ToggleSharedCalendarPayload` | userId: String! | - |
| `uncancelEvent` | `UncancelEventPayload` | eventId: String! | - |
| `uncompleteEvent` | `UncompleteEventPayload` | id: String! | - |
| `unconfirmEvent` | `UnconfirmEventPayload` | id: String! | - |
| `updateBulkAction` | `UpdateBulkActionPayload` | input: PrivateUpdateBulkActionInput!, id: String! | - |
| `updateClient` | `UpdateClientPayload` | id: String!, input: PrivateClientInput! | - |
| `updateClientLog` | `UpdateClientLogPayload` | id: String!, clientId: String!, input: PrivateClientLogInput! | - |
| `updateCompanyFeatureToggles` | `UpdateCompanyFeatureTogglesPayload` | input: PrivateCompanyFeatureTogglesInput! | - |
| `updateCompanySettings` | `UpdateCompanySettingsPayload` | input: PrivateCompanySettingsInput! | - |
| `updateContact` | `UpdateContactPayload` | id: String!, input: PrivateContactInputWithoutNestedCollections! | - |
| `updateContactAddress` | `UpdateContactAddressPayload` | id: String!, input: PrivateContactAddressInput! | - |
| `updateContactEmail` | `UpdateContactEmailPayload` | id: String!, input: PrivateContactEmailInput! | - |
| `updateContactLocation` | `UpdateContactLocationPayload` | id: String!, input: PrivateContactLocationInput! | - |
| `updateContactPhone` | `UpdateContactPhonePayload` | id: String!, input: PrivateContactPhoneInput! | - |
| `updateContactsSortOrder` | `UpdateContactsSortOrderPayload` | clientId: String!, contactIds: [String!]! | - |
| `updateEstimate` | `UpdateEstimatePayload` | input: PrivateUpdateEstimateInput!, id: String! | - |
| `updateEstimateChecklist` | `UpdateEstimateChecklistPayload` | id: String!, input: PrivateEstimateChecklistInput! | - |
| `updateEstimateChecklistGroup` | `UpdateEstimateChecklistGroupPayload` | id: String!, input: PrivateEstimateChecklistGroupInput! | - |
| `updateEstimateChecklistItem` | `UpdateEstimateChecklistItemPayload` | id: String!, input: PrivateEstimateChecklistItemInput! | - |
| `updateEvent` | `UpdateEventPayload` | id: String!, input: PrivateEventInput! | - |
| `updateEventCancelNotice` | `UpdateEventCancelNoticePayload` | id: String!, input: PrivateEventCancelNoticeInput! | - |
| `updateInvoice` | `UpdateInvoicePayload` | id: String!, input: PrivateUpdateInvoiceInput! | - |
| `updateInvoicePayment` | `UpdateInvoicePaymentPayload` | id: String!, input: PrivateInvoicePaymentInput! | - |
| `updateLocalization` | `UpdateLocalizationPayload` | id: String!, input: PrivateLocalizationInput! | - |
| `updateMasterServiceGroup` | `UpdateMasterServiceGroupPayload` | id: String!, input: PrivateMasterServiceGroupInput! | - |
| `updateMasterServiceItem` | `UpdateMasterServiceItemPayload` | id: String!, input: PrivateMasterServiceItemInput! | - |
| `updateOnboarding` | `UpdateOnboardingPayload` | input: PrivateOnboardingInput! | - |
| `updateOnboardingStep` | `UpdateOnboardingStepPayload` | key: String!, dismissed: Boolean! | - |
| `updatePiano` | `UpdatePianoPayload` | id: String!, input: PrivatePianoInput! | - |
| `updatePianoMeasurement` | `UpdatePianoMeasurementPayload` | id: String!, input: PrivatePianoMeasurementInput! | - |
| `updatePianoPhoto` | `UpdatePianoPhotoPayload` | id: String!, input: PrivatePianoPhotoUpdateInput! | - |
| `updateQuickbooksAccountMapping` | `UpdateQuickbooksAccountMappingPayload` | id: String!, input: PrivateQuickbooksAccountMappingInput! | - |
| `updateRecommendation` | `UpdateRecommendationPayload` | id: String!, input: PrivateRecommendationInput! | - |
| `updateRemoteAccountingTaxMapping` | `UpdateRemoteAccountingTaxMappingPayload` | id: String!, input: PrivateRemoteAccountingTaxMappingInput! | - |
| `updateRemoteCalendar` | `UpdateRemoteCalendarPayload` | id: String!, input: PrivateRemoteCalendarInput! | - |
| `updateRemoteCalendarIntegration` | `UpdateRemoteCalendarIntegrationPayload` | id: String!, input: PrivateRemoteCalendarIntegrationInput! | - |
| `updateScheduledMessage` | `UpdateScheduledMessagePayload` | id: String!, input: PrivateScheduledMessageInput! | - |
| `updateScheduledMessageTemplate` | `UpdateScheduledMessageTemplatePayload` | id: String!, input: PrivateScheduledMessageTemplateInput!, updateScheduledMessages: Boolean | - |
| `updateSchedulerAvailability` | `UpdateSchedulerAvailabilityPayload` | id: String!, input: PrivateSchedulerAvailabilityInput! | - |
| `updateSchedulerServiceArea` | `UpdateSchedulerServiceAreaPayload` | id: String!, input: PrivateSchedulerServiceAreaInput! | - |
| `updateSharedCalendar` | `UpdateSharedCalendarPayload` | errorReferenceId: String, id: String!, showEventDetails: Boolean, includeClientPianoDetails: Boolean, eventTypesToShare: [EventType!] | - |
| `updateTax` | `UpdateTaxPayload` | id: String!, name: String, rate: Int, default: Boolean | - |
| `updateUser` | `UpdateUserPayload` | id: String!, input: PrivateUserInput! | - |
| `updateUserFlags` | `UpdateUserFlagsPayload` | input: PrivateUserFlagsInput! | - |
| `updateUserSettings` | `UpdateUserSettingsPayload` | id: String!, input: PrivateUserSettingsInput! | - |
| `validatePhoneNumber` | `ValidatePhoneNumberPayload` | phoneNumber: String! | Takes a phone number in any format and validates whether it is recognized in the company's country. |

---

## Types Objets

*438 types objets disponibles*

### PrivatePiano

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allPianoMeasurements` | `[PrivatePianoMeasurement!]!` | - | - |
| `allPianoPhotos` | `PrivatePianoPhotoConnection!` | after: String, before: String, first: Int, last: Int, search: String, sortBy: [PhotoSort!] | - |
| `calculatedLastService` | `CoreDate` | - | - |
| `calculatedNextService` | `CoreDate` | - | - |
| `caseColor` | `String` | - | - |
| `caseFinish` | `String` | - | - |
| `client` | `PrivateClient` | - | - |
| `company` | `PrivateCompany` | - | - |
| `consignment` | `Boolean` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `damppChaserHumidistatModel` | `String` | - | - |
| `damppChaserInstalled` | `Boolean` | - | - |
| `damppChaserMfgDate` | `CoreDate` | - | - |
| `eventLastService` | `CoreDate` | - | - |
| `hasIvory` | `Boolean` | - | - |
| `id` | `String` | - | - |
| `lifecycleContactPausedUntil` | `CoreDateTime` | - | - |
| `lifecycleState` | `String` | - | - |
| `location` | `String` | - | - |
| `make` | `String` | - | - |
| `manualLastService` | `CoreDate` | - | - |
| `model` | `String` | - | - |
| `needsRepairOrRebuilding` | `Boolean` | - | - |
| `nextServiceOverride` | `CoreDate` | - | - |
| `nextTuningScheduled` | `PrivateEvent` | - | - |
| `notes` | `String` | - | - |
| `playerInstalled` | `Boolean` | - | - |
| `playerMake` | `String` | - | - |
| `playerModel` | `String` | - | - |
| `playerSerialNumber` | `String` | - | - |
| `potentialPerformanceLevel` | `Int` | - | - |
| `primaryPianoPhoto` | `PrivatePianoPhoto` | - | - |
| `referenceId` | `String` | - | - |
| `rental` | `Boolean` | - | - |
| `rentalContractEndsOn` | `CoreDate` | - | - |
| `searchString` | `String` | - | - |
| `serialNumber` | `String` | - | - |
| `serviceIntervalMonths` | `Int` | - | - |
| `size` | `String` | - | - |
| `status` | `PianoStatus` | - | - |
| `tags` | `[String!]!` | - | - |
| `totalLoss` | `Boolean` | - | - |
| `type` | `PianoType` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `useType` | `String` | - | - |
| `year` | `Int` | - | - |

---

### PrivateClient

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allClientsReferred` | `[PrivateClient!]!` | - | - |
| `allContacts` | `PrivateContactConnection!` | after: String, before: String, first: Int, last: Int, includeArchived: Boolean | - |
| `allPianos` | `PrivatePianoConnection!` | after: String, before: String, first: Int, last: Int, status: [PianoStatus!] | - |
| `allScheduledMessages` | `PrivateScheduledMessageConnection!` | after: String, before: String, first: Int, last: Int | - |
| `clientType` | `String` | - | - |
| `company` | `PrivateCompany` | - | - |
| `companyName` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `custom1` | `String` | - | - |
| `custom10` | `String` | - | - |
| `custom2` | `String` | - | - |
| `custom3` | `String` | - | - |
| `custom4` | `String` | - | - |
| `custom5` | `String` | - | - |
| `custom6` | `String` | - | - |
| `custom7` | `String` | - | - |
| `custom8` | `String` | - | - |
| `custom9` | `String` | - | - |
| `defaultBillingContact` | `PrivateContact` | - | - |
| `defaultClientLocalization` | `CoreLocalization!` | - | This is the localization to be used for this client.  You should query this instead of localization because localization may be null.  This defaultClientLocalization field falls through to their preferred technician's setting, and finally down to the company default localization.  This will never be null and should always be the localization to use for displaying things to this client. |
| `defaultContact` | `PrivateContact` | - | - |
| `id` | `String` | - | - |
| `ignoreSafetyChecks` | `Boolean` | - | - |
| `lastInvoice` | `PrivateInvoice` | - | - |
| `lastResultNotes` | `String` | - | - |
| `lifecycle` | `PrivateLifecycle` | - | - |
| `lifecycleState` | `String` | - | - |
| `localization` | `CoreLocalization` | - | This will be null if no localization override has been set for this client. If it is set, this is the localization override (overridden from the company default client localization).  You most likely do not want to use this, but instead should use defaultClientLocalization. |
| `noContactReason` | `String` | - | - |
| `noContactUntil` | `CoreDate` | - | - |
| `personalNotes` | `String` | - | - |
| `preferenceNotes` | `String` | - | - |
| `preferredTechnician` | `PrivateUser` | - | - |
| `preferredTechnicianId` | `String` | - | - |
| `reasonInactiveCode` | `String` | - | - |
| `reasonInactiveDetails` | `String` | - | - |
| `referenceId` | `String` | - | - |
| `referralClient` | `PrivateClient` | - | - |
| `referredBy` | `String` | - | - |
| `referredByNotes` | `String` | - | - |
| `region` | `String` | - | - |
| `searchString` | `String` | - | - |
| `status` | `ClientStatus` | - | - |
| `tags` | `[String!]!` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateContact

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allAddresses` | `PrivateContactAddressConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allEmails` | `PrivateContactEmailConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allLocations` | `PrivateContactLocationConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allPhones` | `PrivateContactPhoneConnection!` | after: String, before: String, first: Int, last: Int | - |
| `archived` | `Boolean!` | - | - |
| `client` | `PrivateClient` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `defaultAddress` | `PrivateContactAddress` | - | - |
| `defaultBillingAddress` | `PrivateContactAddress` | - | - |
| `defaultBillingLocation` | `PrivateContactLocation` | - | - |
| `defaultConfirmedMobilePhone` | `PrivateContactPhone` | - | - |
| `defaultEmail` | `PrivateContactEmail` | - | - |
| `defaultLocation` | `PrivateContactLocation` | - | - |
| `defaultMailingLocation` | `PrivateContactLocation` | - | This will return the ContactLocation that has LocationType ADDRESS and is the default mailing location for this contact. |
| `defaultPhone` | `PrivateContactPhone` | - | - |
| `firstName` | `String` | - | - |
| `id` | `String!` | - | - |
| `isBillingDefault` | `Boolean` | - | - |
| `isDefault` | `Boolean` | - | - |
| `lastName` | `String` | - | - |
| `middleName` | `String` | - | - |
| `role` | `String` | - | - |
| `sortOrder` | `Int` | - | - |
| `suffix` | `String` | - | - |
| `title` | `String` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `wantsEmail` | `Boolean` | - | - |
| `wantsPhone` | `Boolean` | - | - |
| `wantsText` | `Boolean` | - | - |

---

### PrivateLocation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addressLine` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `id` | `String` | - | - |
| `lat` | `Float` | - | - |
| `lng` | `Float` | - | - |
| `name` | `String` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `user` | `PrivateUser` | - | - |

---

### Autres Types Objets

### AddFeatureTrialToSubscriptionPayload

**Description:** Autogenerated return type of AddFeatureTrialToSubscription.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### AddInvoicePaymentPayload

**Description:** Autogenerated return type of AddInvoicePayment.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `invoice` | `PrivateInvoice` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### AddressComponentsPayload

**Description:** Autogenerated return type of AddressComponents.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addressComponents` | `CoreAddressComponents` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### AddressDisplayTemplate

**Description:** This a set of template strings that can be used to display an address for a country.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `countryCode` | `String!` | - | - |
| `multiLine` | `String` | - | - |
| `singleLine` | `String` | - | - |
| `summaryLine` | `String` | - | - |

---

### ApproveEventReservationPayload

**Description:** Autogenerated return type of ApproveEventReservation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `badgeCount` | `PrivateBadgeCount` | - | - |
| `client` | `PrivateClient` | - | - |
| `event` | `PrivateEvent` | - | - |
| `eventReservation` | `PrivateEventReservation` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CancelBillingPlanPayload

**Description:** Autogenerated return type of CancelBillingPlan.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### CancelEventPayload

**Description:** Autogenerated return type of CancelEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CancelPendingBillingPlanCancellationPayload

**Description:** Autogenerated return type of CancelPendingBillingPlanCancellation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### ChangeBillingPlanPayload

**Description:** Autogenerated return type of ChangeBillingPlan.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `currentPlan` | `PrivateJakklopsPricingPlan` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `upcomingPlan` | `PrivateJakklopsPricingPlan` | - | - |

---

### ChangeEventReservationToPendingPayload

**Description:** Autogenerated return type of ChangeEventReservationToPending.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `badgeCount` | `PrivateBadgeCount` | - | - |
| `eventReservation` | `PrivateEventReservation` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### ChangeMasterServiceListPricesPayload

**Description:** Autogenerated return type of ChangeMasterServiceListPrices.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `updatedCount` | `Int!` | - | - |

---

### ChangeOwnPasswordPayload

**Description:** Autogenerated return type of ChangeOwnPassword.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `user` | `PrivateUserWithApiKey` | - | - |

---

### ChooseMailchimpAudiencePayload

**Description:** Autogenerated return type of ChooseMailchimpAudience.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### CompanyInvoiceSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `calculatePianoInvoiceLastService` | `Boolean` | - | Whether or not the invoice date on open/paid invoices to calculate the last service date for pianos. |
| `defaultInvoiceNetDays` | `Int` | - | - |
| `defaultInvoiceNotes` | `String` | - | - |
| `defaultInvoiceNotesHeader` | `String` | - | - |
| `defaultInvoicePaymentType` | `InvoicePaymentType!` | - | - |
| `defaultInvoiceTopNotes` | `String` | - | - |
| `defaultInvoiceTopNotesHeader` | `String` | - | - |
| `defaultUserPaymentOption` | `UserPaymentOption!` | - | - |
| `nextInvoiceNumber` | `Int!` | - | - |
| `showTopNotes` | `Boolean` | - | - |
| `tipsEnabled` | `Boolean!` | - | - |
| `tipsPublicGuiAutoselect` | `Boolean!` | - | - |

---

### CompanyLocalizationSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `defaultClientLocalization` | `CoreLocalization!` | - | This is the localization setting to be used by default for all clients.  Each client can have their own localization that overrides this.  If a client has a preferred technician set, then that user's defaultClientLocalization should be used (if present) before this one.  The check for which client localization to use should be: Client:localization > PreferredTechnician(User):defaultClientLocalization > Company:defaultClientLocalization |
| `defaultCurrency` | `CoreCurrency!` | - | Currently we only support one currency per company, but this may change in the future.  As such, this has been named defaultCurrency in case we later have others.  But for now, assume this is the only one possible. |
| `defaultUserLocalization` | `CoreLocalization!` | - | This is the localization settings to be used by default for all users.  Each user can have their own localization that overrides this, but this is the default for users who have not overridden it. |

---

### CompanySelfSchedulerSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allowCoordinateLocationType` | `Boolean!` | - | - |
| `allowWhat3wordsLocationType` | `Boolean!` | - | - |
| `noAvailabilityMessage` | `I18nString` | - | - |
| `outsideServiceAreaMessage` | `I18nString` | - | - |
| `reservationCompleteBehavior` | `ReservationCompleteBehavior!` | - | - |
| `reservationCompleteMessage` | `I18nString` | - | - |
| `selfSchedulerEnabled` | `Boolean!` | - | - |
| `showCosts` | `Boolean!` | - | - |
| `technicianSelectionBehavior` | `TechnicianSelectionBehavior!` | - | - |
| `welcomeMessage` | `I18nString` | - | - |

---

### CompleteEventPayload

**Description:** Autogenerated return type of CompleteEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `badgeCount` | `PrivateBadgeCount` | - | - |
| `event` | `PrivateEvent` | - | - |
| `invoice` | `PrivateInvoice` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CompletePasswordResetPayload

**Description:** Autogenerated return type of CompletePasswordReset.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isSuccess` | `Boolean!` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### ConfirmEventPayload

**Description:** Autogenerated return type of ConfirmEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CoreAddressComponents

**Description:** This is a street address split into its component parts.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `address1` | `String` | - | - |
| `address2` | `String` | - | - |
| `addressLine` | `String` | - | This is a 1-line representation of the address shown here. |
| `city` | `String` | - | - |
| `countryCode` | `String` | - | - |
| `municipality` | `String` | - | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |
| `state` | `String` | - | - |
| `street1` | `String` | - | - |
| `street2` | `String` | - | - |
| `zip` | `String` | - | - |

---

### CoreCountryInfo

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `alpha2` | `String!` | - | - |
| `emojiFlag` | `String!` | - | - |
| `isGdprRequired` | `Boolean!` | - | - |
| `name` | `String!` | - | - |
| `phonePrefix` | `Int!` | - | - |
| `timezones` | `[String!]!` | - | - |

---

### CoreCurrency

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `code` | `String!` | - | This is the international currency code such as USD, CAD, AUD, etc |
| `decimalDigits` | `Int!` | - | The number of decimal digits to display for fractions of a whole. |
| `divisor` | `Int!` | - | Gazelle returns all currencies as integers.  To get the proper dollar/cents values, you'll need to divide the number and then format it according to the locale.  This is the number to divide by to get the proper decimal. |
| `id` | `String!` | - | - |
| `label` | `String!` | - | The human-readable label to be used to display this currency when selecting options. |
| `symbol` | `String!` | - | The symbol to be used when doing numeric currency formatting such as $, €, £. |

---

### CoreCurrencyValue

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `currency` | `CoreCurrency!` | - | - |
| `id` | `String!` | - | - |
| `value` | `Int!` | - | - |

---

### CoreDateFormat

**Description:** Format strings to be used for formatting dates in a specific locale.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `date` | `CoreFormatStrings!` | - | Format strings for displaying a full date (e.g. 'Jan 1, 2020') |
| `dateTimeSeparator` | `String!` | - | The string to use to separate date and time when you need to display both of them together. |
| `monthYear` | `CoreFormatStrings!` | - | Format strings for displaying just the month and year (e.g. 'Jan 2020') |
| `weekdayDate` | `CoreFormatStrings!` | - | Format strings for displaying a full date with weekday (e.g. 'Wed, Jan 1 2020') |

---

### CoreFieldError

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errorReferenceId` | `String` | - | - |
| `fieldName` | `String` | - | - |
| `key` | `String` | - | - |
| `messages` | `[String!]!` | - | - |
| `type` | `ErrorType!` | - | - |

---

### CoreFormatStrings

**Description:** These are localized format strings that can be used for various date, and time formatters.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `moment` | `String!` | - | A format string for Moment JS |
| `ruby` | `String!` | - | A format string for Ruby's strftime |
| `unicode` | `String!` | - | A format string for Unicode Technical Standard #35 |

---

### CoreGeocodedAddress

**Description:** This returns the latitude and longitude of a string address.  This can be used for displaying a point on a map or doing other location-based services.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addressLine` | `String!` | - | The 1-line string address that was used to generate this lat/lng pair. |
| `lat` | `Float!` | - | The latitude of this address. |
| `lng` | `Float!` | - | The longitude of this address. |
| `locationType` | `String!` | - | The type of location such as ROOFTOP, RANGE_INTERPOLATED, GEOMETRIC_CENTER, or APPROXIMATE |

---

### CoreImage

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `contentType` | `String` | - | - |
| `exists` | `Boolean` | - | - |
| `fileSize` | `Int` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `url` | `String` | - | The URL where you can get this image.  This URL should be public and you can include it directly in an <img> tag or download it. |

---

### CoreImageDetails

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dimensions` | `CoreImageDimensions` | - | - |
| `mimeType` | `String` | - | - |
| `size` | `Int` | - | - |
| `url` | `String` | - | - |

---

### CoreImageDimensions

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `height` | `Int!` | - | - |
| `width` | `Int!` | - | - |

---

### CoreLocalization

**Description:** This contains a set of localization settings to be used for selecting a translation, number, and date formatting.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime` | - | - |
| `currencyFormat` | `CurrencyFormat!` | - | - |
| `dateFormat` | `CoreDateFormat!` | - | The specific date format strings to be used in various cases for the dateFormatLocale that has been set. |
| `dateFormatLocale` | `String!` | - | The pre-defined locale to use for formatting dates.  You most likely don't need this, but instead should query dateFormat directly to get the exact formats for this locale. |
| `firstDayOfWeek` | `Weekdays!` | - | - |
| `id` | `String` | - | - |
| `isClientDefault` | `Boolean!` | - | Whether or not to use this as the default localization for clients that do not have one set, and when their preferred technician does not have one set.  There will only be one localization per company where isClientDefault is true. |
| `isUserDefault` | `Boolean!` | - | Whether or not to use this as the default localization for users that do not have one set.  There will only be one localization per company where isUserDefault is true. |
| `locale` | `String!` | - | The translation to use.  This locale is the index into the specific supported translation. If the locale is unknown, en_US should be used as the default. |
| `numberFormat` | `NumberFormat!` | - | - |
| `timeFormat` | `CoreTimeFormat!` | - | The specific time format strings to be used in various cases for the timeFormatLocal that has been set. |
| `timeFormatLocale` | `String!` | - | The pre-defined locale to use for formatting time.  You most likely don't need this, but instead should query timeFormat directly to get the exact formats for this locale. |
| `updatedAt` | `CoreDateTime` | - | - |

---

### CoreStripePrice

**Description:** This is Stripe's pricing details for a supported country.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `countryCode` | `String!` | - | - |
| `countryLabel` | `String!` | - | - |
| `countryLabelI18n` | `I18nString!` | - | - |
| `link` | `String!` | - | - |
| `rates` | `[CoreStripeRate!]!` | - | - |

---

### CoreStripeRate

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `brands` | `[String!]!` | - | - |
| `label` | `String!` | - | - |
| `rate` | `String!` | - | - |

---

### CoreSupportedLocaleInfo

**Description:** This is the default language and date, time, number formatting for a locale.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dateFormat` | `CoreFormatStrings!` | - | - |
| `dateTimeSeparator` | `String!` | - | - |
| `defaultCurrencyFormat` | `CurrencyFormat!` | - | - |
| `defaultFirstDayOfWeek` | `Weekdays!` | - | - |
| `defaultNumberFormat` | `NumberFormat!` | - | - |
| `isLocaleDefault` | `Boolean!` | - | This tells whether this locale info should be used as the default for this entire language group in cases where the bare language is given.  For example, if the locale is set to 'en', and 'en_US' has isLocaleDefault set to true, then 'en_US' will be used whenever 'en' is requested. |
| `label` | `String!` | - | - |
| `locale` | `String!` | - | - |
| `monthYearFormat` | `CoreFormatStrings!` | - | - |
| `timeFormat` | `CoreFormatStrings!` | - | - |
| `timezoneTimeFormat` | `CoreFormatStrings!` | - | - |
| `weekdayDateFormat` | `CoreFormatStrings!` | - | - |

---

### CoreTimeFormat

**Description:** Format strings to be used for formatting time in a specific locale.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dateTimeSeparator` | `String!` | - | The string to use to separate date and time when you need to display both of them together. |
| `time` | `CoreFormatStrings!` | - | Format strings for displaying time (e.g. '5:30 PM' or '17:00') |
| `timezoneTime` | `CoreFormatStrings!` | - | Format strings for displaying time with a timezone (e.g. '5:30 PM EST') |

---

### CountTimeframeData

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `count` | `Int!` | - | - |
| `date` | `CoreDate!` | - | - |
| `id` | `String!` | - | - |

---

### CountryNameLocalization

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `code` | `String!` | - | - |
| `name` | `String!` | - | - |

---

### CountryNamesLocalization

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `countries` | `[CountryNameLocalization!]!` | - | - |
| `locale` | `String!` | - | - |

---

### CreateAndRunQuickbooksSyncBatchPayload

**Description:** Autogenerated return type of CreateAndRunQuickbooksSyncBatch.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `batchId` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### CreateBulkAddClientTagJobPayload

**Description:** Autogenerated return type of CreateBulkAddClientTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkAddEstimateTagJobPayload

**Description:** Autogenerated return type of CreateBulkAddEstimateTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkAddInvoiceTagJobPayload

**Description:** Autogenerated return type of CreateBulkAddInvoiceTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkAddPianoTagJobPayload

**Description:** Autogenerated return type of CreateBulkAddPianoTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkArchiveEstimateJobPayload

**Description:** Autogenerated return type of CreateBulkArchiveEstimateJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkArchiveInvoiceJobPayload

**Description:** Autogenerated return type of CreateBulkArchiveInvoiceJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkChangeClientStatusJobPayload

**Description:** Autogenerated return type of CreateBulkChangeClientStatusJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkAction` | `PrivateBulkAction` | - | - |
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkChangePianoStatusJobPayload

**Description:** Autogenerated return type of CreateBulkChangePianoStatusJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkAction` | `PrivateBulkAction` | - | - |
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkExportClientsJobPayload

**Description:** Autogenerated return type of CreateBulkExportClientsJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkExportClientsToMailchimpJobPayload

**Description:** Autogenerated return type of CreateBulkExportClientsToMailchimpJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkExportEventsJobPayload

**Description:** Autogenerated return type of CreateBulkExportEventsJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkExportInvoicesJobPayload

**Description:** Autogenerated return type of CreateBulkExportInvoicesJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkExportPianosJobPayload

**Description:** Autogenerated return type of CreateBulkExportPianosJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkMarkAppointmentsCompleteJobPayload

**Description:** Autogenerated return type of CreateBulkMarkAppointmentsCompleteJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkPauseClientsJobPayload

**Description:** Autogenerated return type of CreateBulkPauseClientsJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkAction` | `PrivateBulkAction` | - | - |
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkRecordCallCenterActionJobPayload

**Description:** Autogenerated return type of CreateBulkRecordCallCenterActionJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkAction` | `PrivateBulkAction` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkReminderReassignmentJobPayload

**Description:** Autogenerated return type of CreateBulkReminderReassignmentJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkRemoveClientTagJobPayload

**Description:** Autogenerated return type of CreateBulkRemoveClientTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkRemoveEstimateTagJobPayload

**Description:** Autogenerated return type of CreateBulkRemoveEstimateTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkRemoveInvoiceTagJobPayload

**Description:** Autogenerated return type of CreateBulkRemoveInvoiceTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateBulkRemovePianoTagJobPayload

**Description:** Autogenerated return type of CreateBulkRemovePianoTagJob.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkActions` | `[PrivateBulkAction!]` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateClientLogPayload

**Description:** Autogenerated return type of CreateClientLog.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientLog` | `PrivateClientLog` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateClientPayload

**Description:** Autogenerated return type of CreateClient.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateContactAddressPayload

**Description:** Autogenerated return type of CreateContactAddress.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `address` | `PrivateContactAddress` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateContactEmailPayload

**Description:** Autogenerated return type of CreateContactEmail.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `email` | `PrivateContactEmail` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateContactLocationPayload

**Description:** Autogenerated return type of CreateContactLocation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `location` | `PrivateContactLocation` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateContactPayload

**Description:** Autogenerated return type of CreateContact.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `contact` | `PrivateContact` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateContactPhonePayload

**Description:** Autogenerated return type of CreateContactPhone.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `phone` | `PrivateContactPhone` | - | - |

---

### CreateEstimateChecklistGroupPayload

**Description:** Autogenerated return type of CreateEstimateChecklistGroup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateChecklistGroup` | `PrivateEstimateChecklistGroup` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateEstimateChecklistItemPayload

**Description:** Autogenerated return type of CreateEstimateChecklistItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateChecklistItem` | `PrivateEstimateChecklistItem` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateEstimateChecklistPayload

**Description:** Autogenerated return type of CreateEstimateChecklist.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateChecklist` | `PrivateEstimateChecklist` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateEstimatePayload

**Description:** Autogenerated return type of CreateEstimate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimate` | `PrivateEstimate` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateEventPayload

**Description:** Autogenerated return type of CreateEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateFeatureAccessRequestNoticePayload

**Description:** Autogenerated return type of CreateFeatureAccessRequestNotice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean!` | - | - |

---

### CreateFeatureRequestNoticePayload

**Description:** Autogenerated return type of CreateFeatureRequestNotice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean!` | - | - |

---

### CreateGazelleMailchimpAudiencePayload

**Description:** Autogenerated return type of CreateGazelleMailchimpAudience.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### CreateInvoicePayload

**Description:** Autogenerated return type of CreateInvoice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `invoice` | `PrivateInvoice` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateLocalizationPayload

**Description:** Autogenerated return type of CreateLocalization.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `localization` | `CoreLocalization` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateMasterServiceGroupPayload

**Description:** Autogenerated return type of CreateMasterServiceGroup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `masterServiceGroup` | `PrivateMasterServiceGroup` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateMasterServiceItemPayload

**Description:** Autogenerated return type of CreateMasterServiceItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `masterServiceItem` | `PrivateMasterServiceItem` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreatePianoMeasurementPayload

**Description:** Autogenerated return type of CreatePianoMeasurement.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `pianoMeasurement` | `PrivatePianoMeasurement` | - | - |

---

### CreatePianoPayload

**Description:** Autogenerated return type of CreatePiano.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `piano` | `PrivatePiano` | - | - |

---

### CreatePianoPhotoPayload

**Description:** Autogenerated return type of CreatePianoPhoto.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `pianoPhoto` | `PrivatePianoPhoto` | - | - |

---

### CreateQuickbooksAccountMappingPayload

**Description:** Autogenerated return type of CreateQuickbooksAccountMapping.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `quickbooksAccountMapping` | `PrivateQuickbooksAccountMapping` | - | - |

---

### CreateRecommendationPayload

**Description:** Autogenerated return type of CreateRecommendation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `recommendation` | `PrivateRecommendation` | - | - |

---

### CreateRemoteAccountingTaxMappingPayload

**Description:** Autogenerated return type of CreateRemoteAccountingTaxMapping.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteAccountingTaxMapping` | `PrivateRemoteAccountingTaxMapping` | - | - |

---

### CreateRemoteCalendarIntegrationPayload

**Description:** Autogenerated return type of CreateRemoteCalendarIntegration.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteCalendarIntegration` | `PrivateRemoteCalendarIntegration` | - | - |

---

### CreateRemoteCalendarPayload

**Description:** Autogenerated return type of CreateRemoteCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteCalendar` | `PrivateRemoteCalendar` | - | - |

---

### CreateScheduledMessagePayload

**Description:** Autogenerated return type of CreateScheduledMessage.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `scheduledMessage` | `PrivateScheduledMessage` | - | - |

---

### CreateScheduledMessageTemplatePayload

**Description:** Autogenerated return type of CreateScheduledMessageTemplate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `scheduledMessageTemplate` | `PrivateScheduledMessageTemplate` | - | - |

---

### CreateSchedulerAvailabilityPayload

**Description:** Autogenerated return type of CreateSchedulerAvailability.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `availability` | `PrivateSchedulerAvailability` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateSchedulerServiceAreaPayload

**Description:** Autogenerated return type of CreateSchedulerServiceArea.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `serviceArea` | `PrivateSchedulerServiceArea` | - | - |

---

### CreateSharedCalendarViaAuthPayload

**Description:** Autogenerated return type of CreateSharedCalendarViaAuth.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteCalendar` | `PrivateRemoteCalendar` | - | - |

---

### CreateSharedCalendarViaTokenPayload

**Description:** Autogenerated return type of CreateSharedCalendarViaToken.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### CreateSkipStripePayoutPayload

**Description:** Autogenerated return type of CreateSkipStripePayout.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `skipStripePayout` | `PrivateSkipStripePayout` | - | - |

---

### CreateStripeCheckoutSessionPayload

**Description:** Autogenerated return type of CreateStripeCheckoutSession.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `checkoutId` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateStripeSetupIntentPayload

**Description:** Autogenerated return type of CreateStripeSetupIntent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientSecret` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### CreateTaxPayload

**Description:** Autogenerated return type of CreateTax.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `tax` | `PrivateTax` | - | - |

---

### CreateUserPayload

**Description:** Autogenerated return type of CreateUser.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `user` | `PrivateUser` | - | - |

---

### DashboardLive

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `invoicedToday` | `[CoreCurrencyValue!]!` | - | - |
| `invoicesDue` | `[CoreCurrencyValue!]!` | - | - |
| `paymentsToday` | `[CoreCurrencyValue!]!` | - | - |

---

### DeclineEventReservationPayload

**Description:** Autogenerated return type of DeclineEventReservation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `badgeCount` | `PrivateBadgeCount` | - | - |
| `client` | `PrivateClient` | - | - |
| `eventReservation` | `PrivateEventReservation` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteClientLogPayload

**Description:** Autogenerated return type of DeleteClientLog.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteClientPayload

**Description:** Autogenerated return type of DeleteClient.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteContactAddressPayload

**Description:** Autogenerated return type of DeleteContactAddress.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteContactEmailPayload

**Description:** Autogenerated return type of DeleteContactEmail.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteContactLocationPayload

**Description:** Autogenerated return type of DeleteContactLocation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteContactPayload

**Description:** Autogenerated return type of DeleteContact.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteContactPhonePayload

**Description:** Autogenerated return type of DeleteContactPhone.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteEstimateChecklistGroupPayload

**Description:** Autogenerated return type of DeleteEstimateChecklistGroup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteEstimateChecklistItemPayload

**Description:** Autogenerated return type of DeleteEstimateChecklistItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteEstimateChecklistPayload

**Description:** Autogenerated return type of DeleteEstimateChecklist.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteEstimatePayload

**Description:** Autogenerated return type of DeleteEstimate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteEventPayload

**Description:** Autogenerated return type of DeleteEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteEventReservationPayload

**Description:** Autogenerated return type of DeleteEventReservation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteInvoicePaymentPayload

**Description:** Autogenerated return type of DeleteInvoicePayment.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteLocalizationPayload

**Description:** Autogenerated return type of DeleteLocalization.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteMasterServiceGroupPayload

**Description:** Autogenerated return type of DeleteMasterServiceGroup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteMasterServiceItemPayload

**Description:** Autogenerated return type of DeleteMasterServiceItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeletePianoMeasurementPayload

**Description:** Autogenerated return type of DeletePianoMeasurement.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeletePianoPayload

**Description:** Autogenerated return type of DeletePiano.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeletePianoPhotoPayload

**Description:** Autogenerated return type of DeletePianoPhoto.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeletePushTokenPayload

**Description:** Autogenerated return type of DeletePushToken.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteQuickbooksAccountMappingPayload

**Description:** Autogenerated return type of DeleteQuickbooksAccountMapping.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteRecommendationPayload

**Description:** Autogenerated return type of DeleteRecommendation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteRemoteAccountingTaxMappingPayload

**Description:** Autogenerated return type of DeleteRemoteAccountingTaxMapping.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteRemoteCalendarIntegrationPayload

**Description:** Autogenerated return type of DeleteRemoteCalendarIntegration.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteRemoteCalendarPayload

**Description:** Autogenerated return type of DeleteRemoteCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteScheduledMessagePayload

**Description:** Autogenerated return type of DeleteScheduledMessage.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteScheduledMessageTemplatePayload

**Description:** Autogenerated return type of DeleteScheduledMessageTemplate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteSchedulerAvailabilitiesPayload

**Description:** Autogenerated return type of DeleteSchedulerAvailabilities.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DeleteSchedulerAvailabilityPayload

**Description:** Autogenerated return type of DeleteSchedulerAvailability.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DeleteSchedulerServiceAreaPayload

**Description:** Autogenerated return type of DeleteSchedulerServiceArea.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DeleteSchedulerV2SettingsPayload

**Description:** Autogenerated return type of DeleteSchedulerV2Settings.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DeleteSharedCalendarPayload

**Description:** Autogenerated return type of DeleteSharedCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DeleteSkipStripePayoutPayload

**Description:** Autogenerated return type of DeleteSkipStripePayout.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DeleteTagPayload

**Description:** Autogenerated return type of DeleteTag.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `tags` | `[String!]` | - | - |

---

### DeleteTaxPayload

**Description:** Autogenerated return type of DeleteTax.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isDeleted` | `Boolean` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### DisconnectMailchimpPayload

**Description:** Autogenerated return type of DisconnectMailchimp.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DisconnectQuickbooksOnlinePayload

**Description:** Autogenerated return type of DisconnectQuickbooksOnline.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DisconnectStripePaymentsPayload

**Description:** Autogenerated return type of DisconnectStripePayments.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DismissAllErrorLogsPayload

**Description:** Autogenerated return type of DismissAllErrorLogs.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DismissAllEventCancelNoticesPayload

**Description:** Autogenerated return type of DismissAllEventCancelNotices.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DismissErrorLogPayload

**Description:** Autogenerated return type of DismissErrorLog.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### DismissSystemNotificationPayload

**Description:** Autogenerated return type of DismissSystemNotification.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### EventReservationClientData

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `address1` | `String` | - | - |
| `address2` | `String` | - | - |
| `city` | `String` | - | - |
| `client` | `PrivateClient` | - | The Client record on the requested reservation. |
| `clientId` | `String` | - | The Client id on the requested reservation. |
| `countryCode` | `String` | - | - |
| `email` | `String` | - | - |
| `emailSubscription` | `PrivateEmailSubscription` | - | - |
| `firstName` | `String` | - | - |
| `geocodeType` | `GeocodeLocationType` | - | When the locationType is ADDRESS, this is the type of location returned by the geocoder.  When the locationType is COORDINATES, this will return ROOFTOP. |
| `isGdprConsentAgreed` | `Boolean` | - | - |
| `lastName` | `String` | - | - |
| `lat` | `Float` | - | - |
| `latitude` | `String` | - | When the locationType is ADDRESS, this is the latitude of the location returned by the geocoder.  When the locationType is COORDINATES, this is the latitude of the coordinates.  When the locationType is WHAT3WORDS, this is the converted latitude of the What3Words location. |
| `lng` | `Float` | - | - |
| `locationType` | `ContactLocationType` | - | - |
| `longitude` | `String` | - | When the locationType is ADDRESS, this is the longitude of the location returned by the geocoder.  When the locationType is COORDINATES, this is the longitude of the coordinates.  When the locationType is WHAT3WORDS, this is the converted longitude of the What3Words location. |
| `municipality` | `String` | - | - |
| `phoneNumber` | `String` | - | - |
| `phoneNumberE164` | `String` | - | - |
| `phoneType` | `PhoneType` | - | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |
| `smsOptIn` | `Boolean` | - | - |
| `state` | `String` | - | - |
| `street1` | `String` | - | - |
| `street2` | `String` | - | - |
| `what3words` | `String` | - | When the locationType is WHAT3WORDS, this is the what3words address. |
| `zip` | `String` | - | - |

---

### EventReservationPiano

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isTuning` | `Boolean` | - | - |
| `location` | `String` | - | - |
| `make` | `String` | - | - |
| `model` | `String` | - | - |
| `piano` | `PrivatePiano` | - | The Piano record on the requested reservation. |
| `pianoId` | `String` | - | The Piano id on the requested reservation. |
| `services` | `[EventReservationPianoService!]` | - | - |
| `type` | `PianoType` | - | - |

---

### EventReservationPianoService

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amount` | `Int` | - | - |
| `duration` | `Int` | - | - |
| `name` | `String` | - | - |

---

### GeocodePayload

**Description:** Autogenerated return type of Geocode.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `geocodedAddress` | `CoreGeocodedAddress` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### HistoricalAllTime

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientLifetimeValue` | `[CoreCurrencyValue!]!` | - | - |
| `id` | `String!` | - | - |

---

### HistoricalAppointments

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientsScheduledCount` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `noShowCount` | `Int!` | - | - |
| `pianoTypesServicedCounts` | `[PianoTypeCount!]!` | - | - |
| `pianosServicedCount` | `Int!` | - | - |
| `timeframeData` | `[CountTimeframeData!]!` | - | - |
| `totalCount` | `Int!` | - | - |

---

### HistoricalClientsCreated

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `currentlyActive` | `Int!` | - | - |
| `currentlyInactive` | `Int!` | - | - |
| `currentlyNew` | `Int!` | - | - |
| `currentlyProspect` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `timeframeData` | `[CountTimeframeData!]!` | - | - |
| `totalCount` | `Int!` | - | - |

---

### HistoricalEstimatesCreated

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `convertedCount` | `Int!` | - | - |
| `convertedInvoiceTotal` | `[CoreCurrencyValue!]!` | - | - |
| `currentlyUnexpiredCount` | `Int!` | - | - |
| `estimatedTotal` | `[CoreCurrencyValue!]!` | - | - |
| `id` | `String!` | - | - |
| `timeframeData` | `[CountTimeframeData!]!` | - | - |
| `totalCount` | `Int!` | - | - |

---

### HistoricalInvoicesCreated

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `currentlyDueTotal` | `[CoreCurrencyValue!]!` | - | - |
| `id` | `String!` | - | - |
| `invoicedTotal` | `[CoreCurrencyValue!]!` | - | - |
| `invoicesQuickbooksSyncedCount` | `Int` | - | - |
| `paymentsCount` | `Int!` | - | - |
| `paymentsTotal` | `[CoreCurrencyValue!]!` | - | - |
| `timeframeData` | `[CountTimeframeData!]!` | - | - |
| `totalCount` | `Int!` | - | - |

---

### HistoricalPianosCreated

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `averageAge` | `Int` | - | - |
| `currentlyActive` | `Int!` | - | - |
| `currentlyInTemporaryStorage` | `Int!` | - | - |
| `currentlyInactive` | `Int!` | - | - |
| `currentlyUnderRestoration` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `timeframeData` | `[CountTimeframeData!]!` | - | - |
| `totalCount` | `Int!` | - | - |
| `types` | `[PianoTypeCount!]!` | - | - |

---

### HistoricalPianosDue

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `count` | `Int!` | - | - |
| `date` | `CoreDate!` | - | - |
| `id` | `String!` | - | - |
| `scheduledCount` | `Int!` | - | - |

---

### HistoricalReminders

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `emailCount` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `phoneCount` | `Int!` | - | - |
| `smsCount` | `Int!` | - | - |
| `timeframeData` | `[CountTimeframeData!]!` | - | - |
| `totalCount` | `Int!` | - | - |

---

### HistoricalTimeframe

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `appointments` | `HistoricalAppointments!` | - | - |
| `clientsCreated` | `HistoricalClientsCreated` | - | - |
| `estimatesCreated` | `HistoricalEstimatesCreated!` | - | - |
| `id` | `String!` | - | - |
| `invoicesCreated` | `HistoricalInvoicesCreated!` | - | - |
| `pianosCreated` | `HistoricalPianosCreated` | - | - |
| `pianosDue` | `[HistoricalPianosDue!]` | - | - |
| `reminders` | `HistoricalReminders` | - | - |

---

### ImportServiceLibraryItemsPayload

**Description:** Autogenerated return type of ImportServiceLibraryItems.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### InitiatePasswordResetPayload

**Description:** Autogenerated return type of InitiatePasswordReset.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isSuccess` | `Boolean!` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### JakklopsFeatureTrialAvailability

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `canTrialEstimates` | `Boolean!` | - | - |
| `canTrialInvoices` | `Boolean!` | - | - |
| `canTrialMailchimp` | `Boolean!` | - | - |
| `canTrialQuickbooks` | `Boolean!` | - | - |
| `canTrialReminders` | `Boolean!` | - | - |
| `canTrialScheduling` | `Boolean!` | - | - |
| `canTrialSms` | `Boolean!` | - | - |

---

### LegacyCompanySelfSchedulerSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `outsideServiceAreaMessage` | `String` | - | - |
| `selfScheduleCompletionMessage` | `String` | - | - |
| `selfScheduleCompletionRedirect` | `String` | - | - |
| `selfScheduleSpecialInstructions` | `String` | - | - |

---

### LifecycleTypeAndStateSummary

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `lifecycleState` | `LifecycleState!` | - | - |
| `lifecycleType` | `LifecycleType!` | - | - |
| `reminderType` | `ReminderType!` | - | - |
| `totalClientCount` | `Int!` | - | - |

---

### MergeClientsPayload

**Description:** Autogenerated return type of MergeClients.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### MergePianosPayload

**Description:** Autogenerated return type of MergePianos.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `piano` | `PrivatePiano` | - | - |

---

### MigrateSchedulerV2SettingsPayload

**Description:** Autogenerated return type of MigrateSchedulerV2Settings.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### PageInfo

**Description:** Information about pagination in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `endCursor` | `String` | - | When paginating forwards, the cursor to continue. |
| `hasNextPage` | `Boolean!` | - | When paginating forwards, are there more items? |
| `hasPreviousPage` | `Boolean!` | - | When paginating backwards, are there more items? |
| `startCursor` | `String` | - | When paginating backwards, the cursor to continue. |

---

### PianoTypeCount

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `count` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `type` | `PianoType!` | - | - |

---

### PrivateAuthorizedIntegration

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `authorizedAt` | `CoreDateTime` | - | - |
| `id` | `String` | - | - |
| `name` | `String` | - | - |
| `user` | `PrivateUser` | - | - |

---

### PrivateAvailability

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `endLocation` | `String` | - | - |
| `endLocationLat` | `Float` | - | - |
| `endLocationLng` | `Float` | - | - |
| `endLocationType` | `GeocodeLocationType` | - | - |
| `endOn` | `CoreDate!` | - | - |
| `endTime` | `Int` | - | Will be in the form HMM.  i.e. 830 is 8:30 AM, and 1500 is 3:00 PM, and 0 is 12:00 AM, and 45 is 12:45 AM. |
| `endType` | `AvailabilityLocationType` | - | - |
| `serviceAreaLocation` | `String` | - | - |
| `serviceAreaLocationLat` | `Float` | - | - |
| `serviceAreaLocationLng` | `Float` | - | - |
| `serviceAreaLocationType` | `GeocodeLocationType` | - | - |
| `serviceAreaRadius` | `Int` | - | - |
| `startLocation` | `String` | - | - |
| `startLocationLat` | `Float` | - | - |
| `startLocationLng` | `Float` | - | - |
| `startLocationType` | `GeocodeLocationType` | - | - |
| `startOn` | `CoreDate!` | - | - |
| `startTime` | `Int` | - | Will be in the form HMM.  i.e. 830 is 8:30 AM, and 1500 is 3:00 PM, and 0 is 12:00 AM, and 45 is 12:45 AM. |
| `startType` | `AvailabilityLocationType` | - | - |
| `user` | `PrivateUser!` | - | - |

---

### PrivateBadgeCount

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `eventCancelNotices` | `Int` | - | - |
| `pendingReservations` | `Int` | - | - |
| `uncompletedAppointments` | `Int` | - | - |

---

### PrivateBetaAccess

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimates` | `Boolean!` | - | - |

---

### PrivateBulkAction

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime!` | - | - |
| `description` | `String!` | - | - |
| `emailOnCompletion` | `Boolean!` | - | - |
| `enqueuedBy` | `PrivateUser!` | - | - |
| `errorMessage` | `String` | - | - |
| `id` | `String!` | - | - |
| `jsonArguments` | `String` | - | - |
| `status` | `BulkActionStatus` | - | - |
| `totalComplete` | `Int!` | - | - |
| `totalCount` | `Int!` | - | - |
| `type` | `BulkActionType` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateCallCenterItem

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient!` | - | - |
| `date` | `CoreDate!` | - | - |
| `id` | `String!` | - | - |
| `lifecycle` | `PrivateLifecycle` | - | - |
| `lifecycleContactLog` | `PrivateLifecycleContactLog` | - | - |
| `lifecycleKind` | `String` | - | - |
| `municipality` | `String` | - | - |
| `postalCode` | `String` | - | - |
| `referenceId` | `String!` | - | - |
| `referenceType` | `CallCenterReferenceType!` | - | - |
| `region` | `String` | - | - |
| `reminderKind` | `String` | - | - |
| `reminderState` | `String` | - | - |
| `scheduledMessage` | `PrivateScheduledMessage` | - | - |
| `scheduledMessageTemplate` | `PrivateScheduledMessageTemplate` | - | - |

---

### PrivateCallCenterItemConnection

**Description:** The connection type for PrivateCallCenterItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateCallCenterItemEdge]` | - | A list of edges. |
| `nodes` | `[PrivateCallCenterItem]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateCallCenterItemEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateCallCenterItem` | - | The item at the end of the edge. |

---

### PrivateClientConnection

**Description:** The connection type for PrivateClient.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateClientEdge]` | - | A list of edges. |
| `nodes` | `[PrivateClient]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateClientEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateClient` | - | The item at the end of the edge. |

---

### PrivateClientLog

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `automated` | `Boolean` | - | - |
| `client` | `PrivateClient` | - | - |
| `comment` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `createdBy` | `PrivateUser` | - | - |
| `id` | `String` | - | - |
| `invoice` | `PrivateInvoice` | - | - |
| `piano` | `PrivatePiano` | - | - |
| `status` | `ClientLogStatus` | - | - |
| `systemMessage` | `String` | - | - |
| `type` | `ClientLogType` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `verbose` | `Boolean` | - | - |

---

### PrivateClientLogConnection

**Description:** The connection type for PrivateClientLog.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateClientLogEdge]` | - | A list of edges. |
| `nodes` | `[PrivateClientLog]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateClientLogEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateClientLog` | - | The item at the end of the edge. |

---

### PrivateCompany

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `address1` | `String` | - | - |
| `address2` | `String` | - | - |
| `areAllRemindersPaused` | `Boolean!` | - | - |
| `billablePianoCount` | `Int` | - | - |
| `billablePianoLimit` | `Int` | - | - |
| `billing` | `PrivateCompanyBilling!` | - | - |
| `city` | `String` | - | - |
| `companySmsSettings` | `PrivateCompanySmsSettings!` | - | Extended SMS settings for UIv2 migration - includes verification status, delivery windows, etc. |
| `countryCode` | `String!` | - | - |
| `countryName` | `String!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `currentEmailSender` | `PrivateEmailSender` | - | - |
| `email` | `String` | - | - |
| `gazelleReferral` | `PrivateGazelleReferral` | - | - |
| `gazelleStripeTransactionFee` | `Int!` | - | This returns the fee that Gazelle charges per transaction for payment processing.  This amount is represented in the company's local currency. |
| `id` | `String!` | - | - |
| `isGdprRequired` | `Boolean!` | - | - |
| `isOverBillablePianoLimit` | `Boolean!` | - | - |
| `isParked` | `Boolean!` | - | - |
| `isSmartRoutesEnabled` | `Boolean!` | - | - |
| `lat` | `Float` | - | - |
| `latitude` | `String` | - | - |
| `lng` | `Float` | - | - |
| `logo` | `CoreImage` | - | - |
| `longitude` | `String` | - | - |
| `municipality` | `String` | - | - |
| `name` | `String` | - | - |
| `parkedReason` | `ParkedCompanyReason!` | - | - |
| `phoneNumber` | `String` | format: PhoneFormat | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |
| `settings` | `PrivateCompanySettings!` | - | - |
| `state` | `String` | - | - |
| `street1` | `String` | - | - |
| `street2` | `String` | - | - |
| `stripeCoupon` | `PrivateCompanyStripeCoupon` | - | - |
| `stripeTrialEndsAt` | `CoreDateTime` | - | - |
| `subscriptionLevel` | `Int!` | - | - |
| `supportedStripePaymentMethods` | `[StripePaymentMethods!]!` | - | A list of the Stripe payment methods Gazelle supports in the company country and currency |
| `upcomingMaintenanceNotice` | `PrivateUpcomingMaintenanceNotice` | - | - |
| `urlToken` | `String` | - | - |
| `website` | `String` | - | - |
| `zip` | `String` | - | - |

---

### PrivateCompanyBilling

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `currency` | `CoreCurrency!` | - | - |
| `currentBalance` | `PrivateCompanyBillingCurrentBalance!` | - | The current balance on the Gazelle subscription.  Negative values indicate the next invoice will be decreased by this amount. |
| `defaultPaymentMethodSummary` | `String` | - | - |
| `jakklops` | `PrivateJakklopsCompanyBilling` | - | - |
| `pricingModel` | `PricingModel!` | - | - |
| `showAddressOnInvoices` | `Boolean!` | - | Whether or not the address should be displayed on Gazelle subscription invoices. |
| `showPhoneNumberOnInvoices` | `Boolean!` | - | Whether or not the phone number should be displayed on Gazelle subscription invoices. |
| `showTaxIdsOnInvoices` | `Boolean!` | - | Whether or not the Tax IDs should be displayed on Gazelle subscription invoices. |
| `stripeCustomerAddress` | `StripeAddress` | - | The address that the customer has set on their Stripe Customer record.  This address can be displayed on Gazelle subscription invoices. |
| `stripeCustomerPhoneNumber` | `String` | - | The phone number that the customer has set on their Stripe Customer record.  This phone number can be displayed on Gazelle subscription invoices. |
| `stripeCustomerTaxIds` | `[StripeCustomerTaxId!]` | - | A list of the Tax IDs that the customer has set on their Stripe Customer record.  These Tax IDs can be displayed on Gazelle subscription invoices. |
| `subscriptionStatus` | `SubscriptionStatus!` | - | - |

---

### PrivateCompanyBillingCurrentBalance

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amount` | `Int!` | - | - |
| `currency` | `CoreCurrency!` | - | - |

---

### PrivateCompanyBranding

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `headerLayout` | `CompanyHeaderLayoutType!` | - | - |
| `maxLogoPx` | `Int!` | - | - |
| `primaryColor` | `String` | - | - |
| `privacyPolicy` | `I18nString` | - | - |
| `showCompanyAddress` | `Boolean!` | - | - |
| `showCompanyEmail` | `Boolean!` | - | - |
| `showCompanyPhone` | `Boolean!` | - | - |
| `termsOfService` | `I18nString` | - | - |

---

### PrivateCompanyClientSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `defaultRegion` | `String` | - | - |
| `defaultWantsText` | `Boolean!` | - | - |

---

### PrivateCompanyEstimateSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `defaultMonthsExpiresOn` | `Int` | - | - |
| `defaultNotes` | `I18nString` | - | - |
| `nextEstimateNumber` | `Int` | - | - |
| `sendQuestionsToAllActiveAdmins` | `Boolean` | - | - |
| `sendQuestionsToCreator` | `Boolean` | - | - |
| `sendQuestionsToEmails` | `[String!]` | - | - |

---

### PrivateCompanyGeneralSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `capitalizeNames` | `Boolean!` | - | - |
| `clientCustom10Label` | `String` | - | - |
| `clientCustom1Label` | `String` | - | - |
| `clientCustom2Label` | `String` | - | - |
| `clientCustom3Label` | `String` | - | - |
| `clientCustom4Label` | `String` | - | - |
| `clientCustom5Label` | `String` | - | - |
| `clientCustom6Label` | `String` | - | - |
| `clientCustom7Label` | `String` | - | - |
| `clientCustom8Label` | `String` | - | - |
| `clientCustom9Label` | `String` | - | - |
| `distanceUnit` | `SchedulerDistanceUnitType!` | - | - |
| `headerLayout` | `CompanyHeaderLayoutType` | - | - |
| `hourlyRate` | `BigInt` | - | - |
| `receiptEmail` | `String` | - | - |
| `timezone` | `String` | - | - |

---

### PrivateCompanyLocationBiasSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `lat` | `Float` | - | - |
| `lng` | `Float` | - | - |
| `locationBiasingEnabled` | `Boolean!` | - | - |
| `radius` | `Int` | - | - |

---

### PrivateCompanyMappingSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `geocodeProvider` | `MappingProviderType!` | - | - |
| `interactiveMapProvider` | `MappingProviderType!` | - | - |
| `routeMapProvider` | `MappingProviderType!` | - | - |
| `routePolylineProvider` | `MappingProviderType!` | - | - |
| `staticMapProvider` | `MappingProviderType!` | - | - |
| `typeaheadProvider` | `MappingProviderType!` | - | - |

---

### PrivateCompanyPermissionsSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `assistantsViewCompanyMetrics` | `Boolean!` | - | - |
| `limitedAdminsViewCompanyMetrics` | `Boolean!` | - | - |
| `techniciansViewCompanyMetrics` | `Boolean!` | - | - |

---

### PrivateCompanyPianoSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `defaultServiceIntervalMonths` | `Int` | - | The default number of months between piano tunings. |

---

### PrivateCompanyQuickbooksOnlineSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allowOnlineAchPayment` | `Boolean` | - | When this is true, Gazelle will set the QuickBooks Online AllowOnlineACHPayment property to true when syncing invoices. |
| `allowOnlineCreditCardPayment` | `Boolean` | - | When this is true, Gazelle will set the QuickBooks Online AllowOnlineCreditCardPayment property to true when syncing invoices. |
| `pullPayments` | `Boolean` | - | When this is false, Gazelle will not pull QuickBooks payments into Gazelle by default. |
| `syncGazelleUsersAsQboClasses` | `Boolean!` | - | When set, this will set the Gazelle user who created each invoice as a Quickbooks Online Class.  This can be useful for technician level revenue reporting in Quickbooks Online. |
| `syncStartDate` | `CoreDate!` | - | The date after which Gazelle invoices (and optionally Stripe payouts) will by synced to Quickbooks Online. |
| `syncStripePayouts` | `Boolean` | - | When this is false Gazelle will never sync Stripe Payouts to Quickbooks Online.  When true, this will always sync Stripe Payouts to Quickbooks Online, unless it is overridden for a specific batch. |

---

### PrivateCompanySchedulerSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `includeIcsAttachmentOnNewAppointmentEmails` | `Boolean!` | - | - |
| `invalidAddressDefaultDriveTime` | `Int` | - | - |

---

### PrivateCompanySettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `betaAccess` | `PrivateBetaAccess!` | - | - |
| `branding` | `PrivateCompanyBranding!` | - | - |
| `client` | `PrivateCompanyClientSettings!` | - | - |
| `companySmsSettings` | `PrivateCompanySmsSettings!` | - | Extended SMS settings for UIv2 migration - includes verification status, delivery windows, etc. |
| `estimates` | `PrivateCompanyEstimateSettings!` | - | - |
| `featureToggles` | `PrivateFeatureToggles!` | - | - |
| `general` | `PrivateCompanyGeneralSettings!` | - | - |
| `invoices` | `CompanyInvoiceSettings!` | - | - |
| `legacySelfScheduler` | `LegacyCompanySelfSchedulerSettings!` | - | - |
| `localization` | `CompanyLocalizationSettings!` | - | - |
| `locationBias` | `PrivateCompanyLocationBiasSettings!` | - | - |
| `mapping` | `PrivateCompanyMappingSettings!` | - | - |
| `permissions` | `PrivateCompanyPermissionsSettings!` | - | - |
| `pianos` | `PrivateCompanyPianoSettings!` | - | - |
| `quickbooksOnline` | `PrivateCompanyQuickbooksOnlineSettings!` | - | - |
| `scheduler` | `PrivateCompanySchedulerSettings!` | - | - |
| `selfScheduler` | `CompanySelfSchedulerSettings!` | - | - |
| `sms` | `PrivateCompanySmsSettings!` | - | - |
| `stripePayments` | `PrivateCompanyStripePayments!` | - | - |

---

### PrivateCompanySmsSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `defaultReplyMessage` | `String!` | - | The default message sent when a client replies to an SMS |
| `deliveryWindows` | `[PrivateDeliveryWindow!]!` | - | Time windows during which SMS messages can be delivered |
| `isEnabled` | `Boolean!` | - | Whether or not the company has SMS enabled. SMS must be enabled for the company before SMS reminders can be configured and sent. |
| `phoneNumber` | `String` | format: PhoneFormat | - |
| `requireClientOptIn` | `Boolean!` | - | Whether clients must opt-in to receive SMS messages |
| `verificationStatus` | `SMSVerificationStatus` | - | The verification status of the SMS settings |

---

### PrivateCompanyStripeCoupon

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amountOff` | `Int` | - | - |
| `couponId` | `String!` | - | - |
| `endsAt` | `CoreDateTime` | - | - |
| `percentOff` | `Int` | - | - |

---

### PrivateCompanyStripePayments

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `acceptedPaymentMethods` | `[StripePaymentMethods!]!` | - | A list of the Stripe payment methods this company has chosen to accept |
| `accountId` | `String` | - | - |
| `availableForCountry` | `Boolean!` | - | True if Stripe Payments integration is available for their country. |
| `defaultAcceptElectronicPayments` | `Boolean!` | - | Whether or not new invoices should accept electronic payments by default or not. |
| `stripePublishableKey` | `String!` | - | - |

---

### PrivateContactAddress

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `address1` | `String` | - | - |
| `address2` | `String` | - | - |
| `city` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `geocodeType` | `GeocodeLocationType` | - | - |
| `id` | `String` | - | - |
| `isBadAddress` | `Boolean` | - | - |
| `lat` | `Float` | - | - |
| `lng` | `Float` | - | - |
| `municipality` | `String` | - | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |
| `state` | `String` | - | - |
| `street1` | `String` | - | - |
| `street2` | `String` | - | - |
| `type` | `ContactAddressType!` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `zip` | `String` | - | - |

---

### PrivateContactAddressConnection

**Description:** The connection type for PrivateContactAddress.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateContactAddressEdge]` | - | A list of edges. |
| `nodes` | `[PrivateContactAddress]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateContactAddressEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateContactAddress` | - | The item at the end of the edge. |

---

### PrivateContactConnection

**Description:** The connection type for PrivateContact.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateContactEdge]` | - | A list of edges. |
| `nodes` | `[PrivateContact]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateContactEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateContact` | - | The item at the end of the edge. |

---

### PrivateContactEmail

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `email` | `String` | - | - |
| `emailMd5` | `String` | - | - |
| `id` | `String!` | - | - |
| `isDefault` | `Boolean` | - | - |

---

### PrivateContactEmailConnection

**Description:** The connection type for PrivateContactEmail.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateContactEmailEdge]` | - | A list of edges. |
| `nodes` | `[PrivateContactEmail]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateContactEmailEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateContactEmail` | - | The item at the end of the edge. |

---

### PrivateContactLocation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `countryCode` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `geocodeType` | `GeocodeLocationType` | - | - |
| `id` | `ID` | - | - |
| `isBadAddress` | `Boolean` | - | When the locationType is ADDRESS, this is true if the address does not geocode to a latitude/longitude.  When the locationType is COORDINATES, this will be false. |
| `latitude` | `String` | - | - |
| `locationType` | `LocationType` | - | - |
| `longitude` | `String` | - | - |
| `municipality` | `String` | - | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |
| `street1` | `String` | - | - |
| `street2` | `String` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `usageType` | `ContactLocationUsageType!` | - | - |
| `what3words` | `String` | - | - |

---

### PrivateContactLocationConnection

**Description:** The connection type for PrivateContactLocation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateContactLocationEdge]` | - | A list of edges. |
| `nodes` | `[PrivateContactLocation]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateContactLocationEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateContactLocation` | - | The item at the end of the edge. |

---

### PrivateContactPhone

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `confirmedAt` | `CoreDateTime` | - | - |
| `confirmedCarrier` | `String` | - | - |
| `confirmedClass` | `PhoneClass` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `extension` | `String` | - | - |
| `id` | `String!` | - | - |
| `isDefault` | `Boolean` | - | - |
| `phoneNumber` | `String` | format: PhoneFormat | - |
| `type` | `PhoneType` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateContactPhoneConnection

**Description:** The connection type for PrivateContactPhone.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateContactPhoneEdge]` | - | A list of edges. |
| `nodes` | `[PrivateContactPhone]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateContactPhoneEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateContactPhone` | - | The item at the end of the edge. |

---

### PrivateDashboardMetrics

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `historicalAllTime` | `HistoricalAllTime` | - | - |
| `historicalTimeframe` | `HistoricalTimeframe` | userId: String, startOn: CoreDate!, endOn: CoreDate! | - |
| `id` | `String!` | - | - |
| `live` | `DashboardLive` | userId: String | - |

---

### PrivateDeliveryWindow

**Description:** A time window during which SMS messages can be delivered

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dayOfWeek` | `Weekdays!` | - | The day of the week for this delivery window |
| `endHour` | `Int!` | - | The ending hour for delivery (0-23) |
| `startHour` | `Int!` | - | The starting hour for delivery (0-23) |

---

### PrivateDriveTimes

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errorMessage` | `String` | - | - |
| `errorType` | `DriveTimeErrorType` | - | - |
| `id` | `String` | - | - |
| `secondsWithTraffic` | `Int` | - | - |
| `secondsWithoutTraffic` | `Int` | - | - |

---

### PrivateEmail

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `eventReservation` | `PrivateEventReservation` | - | - |
| `from` | `String` | - | - |
| `htmlBody` | `String` | - | - |
| `id` | `String!` | - | - |
| `invoice` | `PrivateInvoice` | - | - |
| `recipientName` | `String` | - | - |
| `sentAt` | `CoreDateTime` | - | - |
| `status` | `EmailStatus` | - | - |
| `subject` | `String` | - | - |
| `textBody` | `String` | - | - |
| `to` | `String` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateEmailSender

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `fullSenderAddress` | `String!` | - | - |
| `id` | `String!` | - | - |
| `sender` | `String!` | - | - |

---

### PrivateEmailSubscription

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime` | - | - |
| `emailAddress` | `String` | - | - |
| `error` | `String` | - | - |
| `tags` | `[String!]` | - | - |
| `type` | `EmailSubscriptionType` | - | - |

---

### PrivateErrorLog

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `createdAt` | `CoreDate!` | - | - |
| `id` | `String!` | - | - |
| `isDismissed` | `Boolean!` | - | - |
| `message` | `String!` | - | - |
| `occurrenceCount` | `Int!` | - | - |
| `type` | `ErrorLogType!` | - | - |
| `updatedAt` | `CoreDate!` | - | - |

---

### PrivateErrorLogConnection

**Description:** The connection type for PrivateErrorLog.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateErrorLogEdge]` | - | A list of edges. |
| `nodes` | `[PrivateErrorLog]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateErrorLogEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateErrorLog` | - | The item at the end of the edge. |

---

### PrivateEstimate

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateTiers` | `[PrivateEstimateTier!]!` | - | - |
| `assignedTo` | `PrivateUser` | - | - |
| `client` | `PrivateClient!` | - | - |
| `clientUrl` | `String!` | - | - |
| `contact` | `PrivateContact` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `createdBy` | `PrivateUser!` | - | - |
| `currentPerformanceLevel` | `Int` | - | - |
| `estimatedOn` | `CoreDate!` | - | - |
| `expiresOn` | `CoreDate!` | - | - |
| `id` | `String!` | - | - |
| `isArchived` | `Boolean!` | - | - |
| `locale` | `String!` | - | - |
| `notes` | `String` | - | - |
| `number` | `Int!` | - | - |
| `piano` | `PrivatePiano!` | - | - |
| `pianoPhoto` | `PrivatePianoPhoto` | - | - |
| `recommendedTierTotal` | `Int` | - | - |
| `tags` | `[String!]!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateChecklist

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateChecklistGroups` | `[PrivateEstimateChecklistGroup!]!` | - | - |
| `allEstimateChecklistItems` | `[PrivateEstimateChecklistItem!]!` | - | - |
| `allUngroupedEstimateChecklistItems` | `[PrivateEstimateChecklistItem!]!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `id` | `String!` | - | - |
| `isDefault` | `Boolean!` | - | - |
| `name` | `I18nString!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateChecklistGroup

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateChecklistItems` | `[PrivateEstimateChecklistItem!]!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `estimateChecklist` | `PrivateEstimateChecklist!` | - | - |
| `id` | `String!` | - | - |
| `name` | `I18nString!` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateChecklistItem

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime!` | - | - |
| `estimateChecklist` | `PrivateEstimateChecklist!` | - | - |
| `estimateChecklistGroup` | `PrivateEstimateChecklistGroup` | - | - |
| `id` | `String!` | - | - |
| `masterServiceItem` | `PrivateMasterServiceItem` | - | - |
| `name` | `I18nString` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateConnection

**Description:** The connection type for PrivateEstimate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateEstimateEdge]` | - | A list of edges. |
| `nodes` | `[PrivateEstimate]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateEstimateEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateEstimate` | - | The item at the end of the edge. |

---

### PrivateEstimateTier

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateTierGroups` | `[PrivateEstimateTierGroup!]!` | - | - |
| `allEstimateTierItems` | `[PrivateEstimateTierItem!]!` | - | - |
| `allUngroupedEstimateTierItems` | `[PrivateEstimateTierItem!]!` | - | - |
| `allowSelfSchedule` | `Boolean!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `estimate` | `PrivateEstimate!` | - | - |
| `id` | `String!` | - | - |
| `isPrimary` | `Boolean!` | - | - |
| `notes` | `String` | - | - |
| `recommendation` | `PrivateRecommendation` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `subtotal` | `Int!` | - | - |
| `targetPerformanceLevel` | `Int` | - | - |
| `taxTotal` | `Int!` | - | - |
| `total` | `Int!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateTierGroup

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateTierItems` | `[PrivateEstimateTierItem!]!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `estimateTier` | `PrivateEstimateTier!` | - | - |
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateTierItem

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateTierItemPhotos` | `[PrivateEstimateTierItemPhoto!]!` | - | - |
| `amount` | `Int!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `description` | `String` | - | - |
| `duration` | `Int!` | - | - |
| `educationDescription` | `String` | - | - |
| `estimateTier` | `PrivateEstimateTier!` | - | - |
| `estimateTierGroup` | `PrivateEstimateTierGroup` | - | - |
| `externalUrl` | `String` | - | - |
| `id` | `String!` | - | - |
| `isTaxable` | `Boolean!` | - | - |
| `isTuning` | `Boolean!` | - | - |
| `masterServiceItem` | `PrivateMasterServiceItem` | - | - |
| `name` | `String!` | - | - |
| `quantity` | `Int!` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `subtotal` | `Int!` | - | - |
| `taxTotal` | `Int!` | - | - |
| `taxes` | `[PrivateEstimateTierItemTax!]` | - | - |
| `total` | `Int!` | - | - |
| `type` | `MasterServiceItemType!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEstimateTierItemPhoto

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateTierItem` | `PrivateEstimateTierItem!` | - | - |
| `id` | `String` | - | - |
| `pianoPhoto` | `PrivatePianoPhoto!` | - | - |
| `sequenceNumber` | `Int!` | - | - |

---

### PrivateEstimateTierItemTax

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |
| `rate` | `Int!` | - | - |
| `taxId` | `String!` | - | - |
| `total` | `Int!` | - | - |

---

### PrivateEvent

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addressLine` | `String` | - | - |
| `allEventPianos` | `PrivateEventPianoConnection` | after: String, before: String, first: Int, last: Int | - |
| `buffer` | `Int` | - | - |
| `client` | `PrivateClient` | - | - |
| `confirmationWarning` | `EventConfirmationWarning` | - | - |
| `confirmedAt` | `CoreDateTime` | - | - |
| `confirmedByClient` | `Boolean` | - | This will be true if the appointment was confirmed by the client.  Otherwise, if it is not confirmed or if it was confirmed by a company user, then this will be false. |
| `createdAt` | `CoreDateTime` | - | - |
| `createdBy` | `PrivateUser` | - | User who scheduled the event |
| `createdViaSchedulerVersion` | `Int` | - | This is the version of the scheduling algorithm that performed the search that created the event. |
| `duration` | `Int` | - | - |
| `geocodeType` | `GeocodeLocationType` | - | - |
| `id` | `String!` | - | - |
| `impactsSyncedEventAvailability` | `Boolean` | - | - |
| `isAllDay` | `Boolean` | - | - |
| `isTypeChangeable` | `Boolean` | - | - |
| `lat` | `Float` | - | - |
| `lifecycleState` | `String` | - | - |
| `lng` | `Float` | - | - |
| `location` | `PrivateEventLocation` | - | - |
| `manualAddressLine` | `String` | - | This is the manually entered location directly on the event.  It is does not come from a client record. |
| `manualGeocodeType` | `GeocodeLocationType` | - | This is the manually entered geocode type directly on the event.  It is does not come from a client record. |
| `manualLat` | `Float` | - | This is the manually entered location directly on the event.  It is does not come from a client record. |
| `manualLng` | `Float` | - | This is the manually entered location directly on the event.  It is does not come from a client record. |
| `notes` | `String` | - | - |
| `recurrenceDates` | `[Int!]` | - | - |
| `recurrenceEndingDate` | `CoreDate` | - | - |
| `recurrenceEndingOccurrences` | `Int` | - | - |
| `recurrenceEndingType` | `EventRecurrenceEndingType` | - | - |
| `recurrenceId` | `String` | - | - |
| `recurrenceInterval` | `Int` | - | - |
| `recurrenceType` | `EventRecurrenceType` | - | - |
| `recurrenceWeekdays` | `[Int!]` | - | - |
| `recurrenceWeeks` | `[Int!]` | - | - |
| `remoteCalendar` | `PrivateRemoteCalendar` | - | - |
| `remoteType` | `EventType` | - | - |
| `schedulerAvailability` | `PrivateSchedulerAvailability` | - | This is the availability that was used to create this event.  It will be nil if the event was not created from an availability. |
| `source` | `String` | - | The source of the appointment (client_schedule, tech_schedule, manual_schedule) |
| `start` | `CoreDateTime` | - | - |
| `status` | `EventStatus` | - | - |
| `timezone` | `String` | - | - |
| `title` | `String` | - | - |
| `travelMode` | `SchedulerTravelMode` | - | This is the travel mode that will be used for traveling to this event when viewing the itinerary.  It only applies to appointments and personal events. |
| `type` | `EventType` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `user` | `PrivateUser` | - | - |

---

### PrivateEventCancelNotice

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime!` | - | - |
| `event` | `PrivateEvent!` | - | - |
| `id` | `String!` | - | - |
| `status` | `EventCancelNoticeStatus!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateEventCancelNoticeConnection

**Description:** The connection type for PrivateEventCancelNotice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateEventCancelNoticeEdge]` | - | A list of edges. |
| `nodes` | `[PrivateEventCancelNotice]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateEventCancelNoticeEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateEventCancelNotice` | - | The item at the end of the edge. |

---

### PrivateEventConnection

**Description:** The connection type for PrivateEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateEventEdge]` | - | A list of edges. |
| `nodes` | `[PrivateEvent]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateEventEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateEvent` | - | The item at the end of the edge. |

---

### PrivateEventLocation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `countryCode` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `geocodeType` | `GeocodeLocationType` | - | - |
| `id` | `ID` | - | - |
| `latitude` | `String` | - | - |
| `locationType` | `EventLocationType` | - | - |
| `longitude` | `String` | - | - |
| `municipality` | `String` | - | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |
| `singleLineAddress` | `String` | - | - |
| `street1` | `String` | - | - |
| `street2` | `String` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `what3words` | `String` | - | - |

---

### PrivateEventPiano

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent!` | - | - |
| `isTuning` | `Boolean!` | - | - |
| `piano` | `PrivatePiano!` | - | - |

---

### PrivateEventPianoConnection

**Description:** The connection type for PrivateEventPiano.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateEventPianoEdge]` | - | A list of edges. |
| `nodes` | `[PrivateEventPiano]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateEventPianoEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateEventPiano` | - | The item at the end of the edge. |

---

### PrivateEventReservation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addressLine` | `String` | - | - |
| `buffer` | `Int` | - | - |
| `changes` | `[String!]!` | - | - |
| `client` | `PrivateClient` | - | The approved Client record. |
| `clientData` | `EventReservationClientData` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `createdViaSchedulerVersion` | `Int` | - | This is the version of the scheduling algorithm that performed the search that created the reservation. |
| `duration` | `Int` | - | - |
| `estimateTier` | `PrivateEstimateTier` | - | - |
| `event` | `PrivateEvent` | - | - |
| `id` | `String` | - | - |
| `notes` | `String` | - | - |
| `pianoServices` | `[EventReservationPiano!]` | - | - |
| `schedulerAvailability` | `PrivateSchedulerAvailability` | - | This is the availability that was used to create slot that was chosen for this reservation. |
| `schedulerV2SearchId` | `String` | - | - |
| `source` | `EventReservationSource` | - | - |
| `startsAt` | `CoreDateTime` | - | - |
| `status` | `EventReservationStatus` | - | - |
| `statusChangedAt` | `CoreDateTime` | - | - |
| `statusChangedBy` | `PrivateUser` | - | - |
| `timezone` | `String` | - | - |
| `travelMode` | `SchedulerTravelMode` | - | - |
| `type` | `EventReservationType` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |
| `user` | `PrivateUser` | - | - |

---

### PrivateEventReservationConnection

**Description:** The connection type for PrivateEventReservation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateEventReservationEdge]` | - | A list of edges. |
| `nodes` | `[PrivateEventReservation]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateEventReservationEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateEventReservation` | - | The item at the end of the edge. |

---

### PrivateFeatureToggles

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `accountingIntegrationsEnabled` | `Boolean!` | - | - |
| `calendarIntegrationsEnabled` | `Boolean!` | - | - |
| `estimatesEnabled` | `Boolean!` | - | - |
| `gazelleCalendarIntegrationsEnabled` | `Boolean!` | - | - |
| `invoicesUiv2Enabled` | `Boolean!` | - | - |
| `publicV2Allowed` | `Boolean!` | - | Whether or not the company is allowed to use the new client interface. |
| `publicV2Enabled` | `Boolean!` | - | Whether or not the company is currently using the new client interface. |
| `qboIntegrationEnabled` | `Boolean!` | - | Whether or not the company can use the new QuickBooks Online Canada support. |
| `schedulerV2Allowed` | `Boolean!` | - | Whether or not the company is allowed to use the new scheduler. |
| `schedulerV2CanDowngrade` | `Boolean!` | - | Whether or not the company is allowed to downgrade to the legacy scheduler. |
| `schedulerV2Enabled` | `Boolean!` | - | Whether or not the company is currently using the new scheduler. |
| `stripePaymentsEnabled` | `Boolean!` | - | - |

---

### PrivateFeatureTrial

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `feature` | `PrivateJakklopsPricingFeatureType!` | - | - |
| `id` | `String!` | - | - |
| `shouldAddToStripeSubscription` | `Boolean!` | - | If true, the feature will be added to the Stripe subscription when the feature trial ends. |
| `trialEndsAt` | `CoreDateTime!` | - | - |
| `trialStartsAt` | `CoreDateTime!` | - | - |

---

### PrivateGazelleReferral

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `email` | `String!` | - | - |
| `hasBeenPaidOut` | `Boolean!` | - | - |
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |
| `referralToken` | `String!` | - | - |
| `referredOn` | `CoreDate!` | - | - |
| `status` | `GazelleReferralStatus!` | - | - |
| `user` | `PrivateUser!` | - | - |

---

### PrivateGlobalConfig

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `azk` | `String!` | - | - |
| `gak` | `String!` | - | - |
| `gmk` | `String!` | - | - |
| `gsk` | `String!` | - | - |
| `intercomAppId` | `String!` | - | - |
| `mbpk` | `String!` | - | - |
| `stripePublishableKey` | `String!` | - | - |
| `w3w` | `String!` | - | - |

---

### PrivateGoogleCalendar

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |

---

### PrivateInvoice

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `acceptElectronicPayment` | `Boolean` | - | - |
| `acceptedElectronicPaymentMethods` | `[StripePaymentMethods!]` | - | A list of the Stripe payment methods available to this invoice |
| `allClientLogs` | `PrivateClientLogConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allInvoiceItems` | `PrivateInvoiceItemConnection!` | after: String, before: String, first: Int, last: Int | - |
| `allInvoicePayments` | `PrivateInvoicePaymentConnection!` | after: String, before: String, first: Int, last: Int | - |
| `altBillingAddress1` | `String` | - | - |
| `altBillingAddress2` | `String` | - | - |
| `altBillingCity` | `String` | - | - |
| `altBillingCompanyName` | `String` | - | - |
| `altBillingCountryCode` | `String` | - | - |
| `altBillingEmail` | `String` | - | - |
| `altBillingFirstName` | `String` | - | - |
| `altBillingLastName` | `String` | - | - |
| `altBillingMunicipality` | `String` | - | - |
| `altBillingPhone` | `String` | - | - |
| `altBillingPostalCode` | `String` | - | - |
| `altBillingRegion` | `String` | - | - |
| `altBillingState` | `String` | - | - |
| `altBillingStreet1` | `String` | - | - |
| `altBillingStreet2` | `String` | - | - |
| `altBillingZip` | `String` | - | - |
| `archived` | `Boolean` | - | - |
| `assignedTo` | `PrivateUser` | - | - |
| `client` | `PrivateClient` | - | - |
| `clientUrl` | `String!` | - | - |
| `company` | `PrivateCompany` | - | - |
| `contact` | `PrivateContact` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `createdBy` | `PrivateUser` | - | - |
| `currency` | `CoreCurrency!` | - | - |
| `dueOn` | `CoreDate` | - | - |
| `dueTotal` | `Int` | - | - |
| `hasPaymentPending` | `Boolean!` | - | True if the most recently created invoice payment is pending. |
| `hasPaymentsPending` | `Boolean!` | - | - |
| `hasQuickbooksSyncNotices` | `Boolean` | - | Whether or not this invoice has any notices from syncing between Gazelle and QuickBooks Online. |
| `id` | `String` | - | - |
| `lastQuickbooksSyncAt` | `CoreDateTime` | - | - |
| `needsQuickbooksSync` | `Boolean` | - | - |
| `netDays` | `Int` | - | - |
| `notes` | `String` | - | - |
| `notesHeader` | `String` | - | - |
| `number` | `Int` | - | - |
| `paidTotal` | `Int` | - | - |
| `quickbooksSyncNotices` | `[PrivateQuickbooksSyncNotice!]!` | - | A list of any notices (not errors) related to the last sync of this invoice. |
| `searchString` | `String` | - | - |
| `status` | `InvoiceStatus` | - | - |
| `subTotal` | `Int` | - | - |
| `summarize` | `Boolean` | - | - |
| `tags` | `[String!]!` | - | - |
| `taxTotal` | `Int` | - | - |
| `tipTotal` | `Int` | - | - |
| `topNotes` | `String` | - | - |
| `topNotesHeader` | `String` | - | - |
| `total` | `Int` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateInvoiceConnection

**Description:** The connection type for PrivateInvoice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateInvoiceEdge]` | - | A list of edges. |
| `nodes` | `[PrivateInvoice]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateInvoiceEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateInvoice` | - | The item at the end of the edge. |

---

### PrivateInvoiceItem

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amount` | `Int` | - | - |
| `billable` | `Boolean` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `description` | `String` | - | - |
| `id` | `String` | - | - |
| `masterServiceItem` | `PrivateMasterServiceItem` | - | - |
| `piano` | `PrivatePiano` | - | - |
| `quantity` | `Int` | - | - |
| `sequenceNumber` | `Int` | - | - |
| `subTotal` | `Int` | - | - |
| `taxTotal` | `Int` | - | - |
| `taxable` | `Boolean` | - | - |
| `taxes` | `[PrivateInvoiceItemTax!]!` | - | - |
| `total` | `Int` | - | - |
| `type` | `InvoiceItemType` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateInvoiceItemConnection

**Description:** The connection type for PrivateInvoiceItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateInvoiceItemEdge]` | - | A list of edges. |
| `nodes` | `[PrivateInvoiceItem]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateInvoiceItemEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateInvoiceItem` | - | The item at the end of the edge. |

---

### PrivateInvoiceItemTax

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |
| `rate` | `Int!` | - | - |
| `taxId` | `String!` | - | - |
| `total` | `Int!` | - | - |

---

### PrivateInvoicePayment

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amount` | `Int!` | - | The total amount of this payment, inclusive of any tip. |
| `createdAt` | `CoreDateTime!` | - | - |
| `currency` | `CoreCurrency!` | - | - |
| `failureReason` | `String` | - | If the payment failed, this is the reason |
| `id` | `String!` | - | The id of this payment. |
| `invoice` | `PrivateInvoice!` | - | The invoice this payment is associated with. |
| `isStripePayment` | `Boolean!` | - | Indicates if this payment was processed through Stripe. |
| `isSyncedToQuickbooksOnline` | `Boolean!` | - | Indicates if this payment has been synced to QuickBooks Online. |
| `notes` | `String` | - | Any notes from this payment. |
| `paidAt` | `CoreDateTime` | - | - |
| `paymentDetails` | `String` | - | Any additional details if Gazelle processed the payment on your behalf.  This will be null if the payment was not processed through a Gazelle payment integration. |
| `paymentSource` | `InvoicePaymentSource!` | - | Indicates the original source of this payment. |
| `status` | `InvoicePaymentStatus!` | - | The status of this payment. |
| `tipTotal` | `Int!` | - | The portion (if any) of the payment amount that was a tip. |
| `type` | `InvoicePaymentType!` | - | The type of this payment. |
| `wasInitiatedByClient` | `Boolean` | - | Indicates if the client clicked the "Pay Now" button on an invoice to make this payment. |

---

### PrivateInvoicePaymentConnection

**Description:** The connection type for PrivateInvoicePayment.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateInvoicePaymentEdge]` | - | A list of edges. |
| `nodes` | `[PrivateInvoicePayment]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateInvoicePaymentEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateInvoicePayment` | - | The item at the end of the edge. |

---

### PrivateJakklopsBillingInvoice

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amountDue` | `Int!` | - | The total amount that is actually due after all adjustments. |
| `appliedBalance` | `Int!` | - | Any balance or credit that was applied to this invoice. |
| `coupons` | `[PrivateJakklopsInvoiceDiscountAmount!]!` | - | - |
| `currency` | `CoreCurrency!` | - | - |
| `discountAmounts` | `[PrivateJakklopsInvoiceDiscountAmount!]!` | - | - |
| `id` | `String!` | - | - |
| `lines` | `[PrivateUpcomingJakklopsBillingInvoiceLine!]!` | - | - |
| `nextPaymentAttempt` | `CoreDateTime` | - | - |
| `subtotal` | `Int!` | - | Subtotal before any coupons. |
| `total` | `Int!` | - | The total of this invoice before any balance or credits are applied. |

---

### PrivateJakklopsCompanyBilling

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `billingCycleEndDate` | `CoreDate` | - | - |
| `coupons` | `[PrivateJakklopsDiscount!]!` | - | - |
| `currentPlan` | `PrivateJakklopsPricingPlan` | - | - |
| `currentPlanWillCancel` | `Boolean!` | - | If the Gazelle subscription plan has been cancelled and will not renew at the end of the billing cycle, this will be true. |
| `discounts` | `[PrivateJakklopsDiscount!]!` | - | - |
| `freeTrialEndsOn` | `CoreDate` | - | A null value indicates the current plan is not on a trial. |
| `projectedSubscriptionChange` | `PrivateJakklopsProjectedSubscriptionChange!` | activePianoLimit: Int!, features: [PrivateJakklopsPricingFeatureType!]!, interval: PricingModelInterval! | - |
| `stripePortalSessionUrl` | `String` | returnUrl: String | - |
| `upcomingInvoice` | `PrivateJakklopsBillingInvoice` | - | - |
| `upcomingPlan` | `PrivateJakklopsPricingPlan` | - | This will be null if there there are no changes to the Gazelle subscription that will take effect in the future, OR if the current subscription has been cancelled. |

---

### PrivateJakklopsDiscount

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `String!` | - | - |
| `endsOn` | `CoreDate` | - | A null value here indicates the coupon never expires. |
| `id` | `String!` | - | - |

---

### PrivateJakklopsInvoiceDiscountAmount

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amount` | `Int!` | - | - |
| `description` | `String` | - | - |
| `endsOn` | `CoreDate!` | - | - |
| `id` | `String!` | - | - |

---

### PrivateJakklopsPricing

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allFeatures` | `[PrivateJakklopsPricingFeature!]!` | - | - |
| `allPlansUrl` | `String!` | countryCode: String! | This will return a URL to a JSON blob with all the plans for a given country. |
| `allTiers` | `[Int!]!` | - | - |

---

### PrivateJakklopsPricingFeature

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `I18nString!` | - | - |
| `id` | `PrivateJakklopsPricingFeatureType!` | - | - |
| `name` | `I18nString!` | - | - |
| `requires` | `[PrivateJakklopsPricingFeatureType!]!` | - | - |
| `type` | `PrivateJakklopsPricingFeatureType!` | - | - |

---

### PrivateJakklopsPricingPlan

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `activePianoLimit` | `Int!` | - | - |
| `amount` | `Int!` | - | - |
| `currency` | `CoreCurrency!` | - | - |
| `currentFeatureTrials` | `[PrivateFeatureTrial!]!` | - | - |
| `featureTrialAvailability` | `JakklopsFeatureTrialAvailability!` | - | - |
| `features` | `[PrivateJakklopsPricingFeature!]!` | - | - |
| `id` | `String!` | - | - |
| `interval` | `PricingModelInterval!` | - | - |
| `name` | `String!` | - | - |
| `pastFeatureTrials` | `[PrivateFeatureTrial!]!` | - | - |

---

### PrivateJakklopsProjectedSubscriptionChange

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amountDueToday` | `Int!` | - | - |
| `balanceUsedToday` | `Int!` | - | - |
| `newSubscriptionRate` | `Int!` | - | - |
| `nextBillingCycleEndAt` | `CoreDateTime!` | - | - |

---

### PrivateLegalContract

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `contractDate` | `CoreDate!` | - | - |
| `contractHtml` | `String!` | language: String | - |
| `explanation` | `I18nString!` | - | - |
| `id` | `String!` | - | This ID will be unique for each version of a legal contract.  So if the EU GDPR SCCs have 4 different versions, there will be 4 different LegalContracts each with its own unique id. |
| `signedAt` | `CoreDateTime` | - | - |
| `signedBy` | `PrivateUser` | - | - |
| `title` | `I18nString!` | - | - |
| `type` | `LegalContractType!` | - | - |
| `version` | `String!` | - | - |

---

### PrivateLifecycle

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `confWindowCode` | `String` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `id` | `String` | - | - |
| `name` | `String` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateLifecycleConnection

**Description:** The connection type for PrivateLifecycle.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateLifecycleEdge]` | - | A list of edges. |
| `nodes` | `[PrivateLifecycle]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateLifecycleContactLog

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient!` | - | - |
| `completedAt` | `CoreDateTime` | - | - |
| `count` | `Int!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `dueAt` | `CoreDateTime` | - | - |
| `event` | `PrivateEvent` | - | - |
| `id` | `String` | - | - |
| `lifecycle` | `PrivateLifecycle` | - | - |
| `lifecycleKind` | `String!` | - | - |
| `lifecycleState` | `String!` | - | - |
| `piano` | `PrivatePiano` | - | - |
| `reminderKind` | `String!` | - | - |
| `state` | `String!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateLifecycleEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateLifecycle` | - | The item at the end of the edge. |

---

### PrivateMailchimpAudience

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String` | - | - |
| `name` | `String` | - | - |

---

### PrivateMailchimpIntegration

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `chosenAudienceId` | `String` | - | - |
| `isConnected` | `Boolean` | - | - |
| `isConnectedPassive` | `Boolean` | - | - |

---

### PrivateMasterServiceGroup

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allMasterServiceItems` | `[PrivateMasterServiceItem!]!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `estimateChecklistCount` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `isArchived` | `Boolean!` | - | - |
| `isMultiChoice` | `Boolean!` | - | - |
| `name` | `I18nString!` | - | - |
| `order` | `Int!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateMasterServiceItem

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allEstimateChecklistItems` | `[PrivateEstimateChecklistItem!]!` | - | - |
| `allEstimateTierItems` | `[PrivateEstimateTierItem!]!` | - | - |
| `allUsers` | `[PrivateUser!]!` | - | - |
| `amount` | `Int` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `description` | `I18nString!` | - | - |
| `duration` | `Int!` | - | - |
| `educationDescription` | `I18nString!` | - | - |
| `externalUrl` | `String` | - | - |
| `id` | `String!` | - | - |
| `isAnyUser` | `Boolean!` | - | - |
| `isArchived` | `Boolean!` | - | - |
| `isDefault` | `Boolean!` | - | - |
| `isSelfSchedulable` | `Boolean!` | - | - |
| `isTaxable` | `Boolean!` | - | - |
| `isTuning` | `Boolean!` | - | - |
| `masterServiceGroup` | `PrivateMasterServiceGroup!` | - | - |
| `name` | `I18nString!` | - | - |
| `order` | `Int!` | - | - |
| `type` | `MasterServiceItemType!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateNextLifecycleMessage

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `dueAt` | `CoreDateTime` | - | - |
| `event` | `PrivateEvent` | - | - |
| `isMissingContactInfo` | `Boolean` | - | - |
| `isRecentlyChanged` | `Boolean` | - | - |
| `lifecycleState` | `LifecycleState` | - | - |
| `lifecycleType` | `LifecycleType` | - | - |
| `message` | `String` | - | - |
| `piano` | `PrivatePiano` | - | - |
| `reminderType` | `ReminderType` | - | - |

---

### PrivateNextLifecycleMessageConnection

**Description:** The connection type for PrivateNextLifecycleMessage.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateNextLifecycleMessageEdge]` | - | A list of edges. |
| `nodes` | `[PrivateNextLifecycleMessage]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateNextLifecycleMessageEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateNextLifecycleMessage` | - | The item at the end of the edge. |

---

### PrivateOnboarding

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `selectedTier` | `Int` | - | - |
| `steps` | `[PrivateOnboardingStep!]!` | - | - |
| `visible` | `Boolean!` | - | - |

---

### PrivateOnboardingStep

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dismissed` | `Boolean!` | - | - |
| `key` | `String!` | - | - |
| `label` | `String!` | - | - |
| `tiers` | `[Int!]!` | - | - |

---

### PrivatePianoConnection

**Description:** The connection type for PrivatePiano.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivatePianoEdge]` | - | A list of edges. |
| `nodes` | `[PrivatePiano]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivatePianoEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivatePiano` | - | The item at the end of the edge. |

---

### PrivatePianoMeasurement

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `a0Dip` | `Int` | - | - |
| `a0Pitch` | `Int` | - | - |
| `a1Dip` | `Int` | - | - |
| `a1Pitch` | `Int` | - | - |
| `a2Dip` | `Int` | - | - |
| `a2Pitch` | `Int` | - | - |
| `a3Dip` | `Int` | - | - |
| `a3Pitch` | `Int` | - | - |
| `a4Dip` | `Int` | - | - |
| `a4Pitch` | `Int` | - | - |
| `a5Dip` | `Int` | - | - |
| `a5Pitch` | `Int` | - | - |
| `a6Dip` | `Int` | - | - |
| `a6Pitch` | `Int` | - | - |
| `a7Dip` | `Int` | - | - |
| `a7Pitch` | `Int` | - | - |
| `c7SustainPlayed` | `Int` | - | - |
| `c7SustainPlucked` | `Int` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `d6SustainPlayed` | `Int` | - | - |
| `d6SustainPlucked` | `Int` | - | - |
| `g6SustainPlayed` | `Int` | - | - |
| `g6SustainPlucked` | `Int` | - | - |
| `humidity` | `Int` | - | - |
| `id` | `String` | - | - |
| `pianoId` | `String` | - | - |
| `takenOn` | `CoreDate` | - | - |
| `temperature` | `Int` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivatePianoPhoto

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime` | - | - |
| `id` | `String` | - | - |
| `isUsedByEstimates` | `Boolean` | - | - |
| `notes` | `String` | - | - |
| `original` | `CoreImageDetails` | - | - |
| `pianoId` | `String` | - | - |
| `takenAt` | `CoreDateTime` | - | - |
| `thumbnail` | `CoreImageDetails` | - | - |

---

### PrivatePianoPhotoConnection

**Description:** The connection type for PrivatePianoPhoto.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivatePianoPhotoEdge]` | - | A list of edges. |
| `nodes` | `[PrivatePianoPhoto]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivatePianoPhotoEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivatePianoPhoto` | - | The item at the end of the edge. |

---

### PrivatePricing

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `affiliate` | `PrivatePricingAffiliate` | - | - |
| `gdprCountryCodes` | `[String!]!` | - | - |
| `jakklops` | `PrivateJakklopsPricing!` | - | - |
| `quickbooksIntegrationFees` | `[PrivateQuickbooksIntegrationFee!]!` | - | - |
| `smsFees` | `[PrivatePricingSmsFee!]!` | - | - |
| `tiers` | `PrivatePricingTiers!` | - | - |

---

### PrivatePricingAffiliate

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `code` | `String!` | - | - |
| `discountDuration` | `String!` | - | - |
| `discountMultiplier` | `Float!` | - | - |
| `extraFields` | `[PrivatePricingExtraField!]!` | - | - |
| `name` | `String!` | - | - |
| `signupBlurb` | `String!` | - | - |

---

### PrivatePricingExtraField

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `key` | `String!` | - | - |
| `label` | `String!` | - | - |

---

### PrivatePricingSmsFee

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cost` | `Int!` | - | - |
| `countryCode` | `String!` | - | - |
| `countryName` | `String!` | - | - |

---

### PrivatePricingTier

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `baseCost` | `Int!` | - | - |
| `extraUserCost` | `Int` | - | - |
| `name` | `String!` | - | - |
| `schedulerCost` | `Int!` | - | - |

---

### PrivatePricingTiers

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `free` | `PrivatePricingTier!` | - | - |
| `professional` | `PrivatePricingTier!` | - | - |
| `startup` | `PrivatePricingTier!` | - | - |

---

### PrivateQuickbooksAccountMapping

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `quickbooksAccountId` | `String!` | - | - |
| `type` | `QuickbooksAccountType!` | - | - |

---

### PrivateQuickbooksIntegrationFee

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cost` | `Int!` | - | - |
| `countryCode` | `String!` | - | - |
| `countryName` | `String!` | - | - |
| `supportLevel` | `QuickbooksSupportLevel!` | - | - |

---

### PrivateQuickbooksSyncBatch

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `batchLevelErrors` | `[PrivateQuickbooksSyncError!]!` | - | - |
| `batchLevelNotices` | `[PrivateQuickbooksSyncNotice!]!` | - | - |
| `completedAt` | `CoreDateTime` | - | - |
| `id` | `String!` | - | - |
| `initiatedAt` | `CoreDateTime` | - | - |
| `initiatedBy` | `PrivateUser!` | - | - |
| `status` | `QuickbooksBatchSyncStatus!` | - | - |
| `syncInvoices` | `PrivateQuickbooksSyncInvoiceConnection!` | after: String, before: String, first: Int, last: Int | - |
| `syncQuickbooksPayments` | `PrivateQuickbooksSyncQuickbooksPaymentsConnection!` | after: String, before: String, first: Int, last: Int | - |
| `syncStripePayouts` | `PrivateQuickbooksSyncStripePayoutConnection!` | after: String, before: String, first: Int, last: Int | - |

---

### PrivateQuickbooksSyncBatchConnection

**Description:** The connection type for PrivateQuickbooksSyncBatch.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateQuickbooksSyncBatchEdge]` | - | A list of edges. |
| `nodes` | `[PrivateQuickbooksSyncBatch]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateQuickbooksSyncBatchEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateQuickbooksSyncBatch` | - | The item at the end of the edge. |

---

### PrivateQuickbooksSyncError

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `String!` | - | - |
| `title` | `String` | - | - |
| `type` | `QuickbooksSyncErrorType` | - | - |
| `url` | `String` | - | - |

---

### PrivateQuickbooksSyncInvoice

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errors` | `[PrivateQuickbooksSyncError!]!` | - | - |
| `id` | `String!` | - | - |
| `invoice` | `PrivateInvoice` | - | - |
| `notices` | `[PrivateQuickbooksSyncNotice!]!` | - | - |
| `status` | `QuickbooksSyncStatus!` | - | - |

---

### PrivateQuickbooksSyncInvoiceConnection

**Description:** The connection type for PrivateQuickbooksSyncInvoice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateQuickbooksSyncInvoiceEdge]` | - | A list of edges. |
| `nodes` | `[PrivateQuickbooksSyncInvoice]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateQuickbooksSyncInvoiceEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateQuickbooksSyncInvoice` | - | The item at the end of the edge. |

---

### PrivateQuickbooksSyncNotice

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `String!` | - | - |
| `type` | `QuickbooksSyncNoticeType` | - | - |

---

### PrivateQuickbooksSyncQuickbooksPayments

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errors` | `[PrivateQuickbooksSyncError!]!` | - | - |
| `id` | `String!` | - | - |
| `status` | `QuickbooksSyncStatus!` | - | - |

---

### PrivateQuickbooksSyncQuickbooksPaymentsConnection

**Description:** The connection type for PrivateQuickbooksSyncQuickbooksPayments.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateQuickbooksSyncQuickbooksPaymentsEdge]` | - | A list of edges. |
| `nodes` | `[PrivateQuickbooksSyncQuickbooksPayments]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateQuickbooksSyncQuickbooksPaymentsEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateQuickbooksSyncQuickbooksPayments` | - | The item at the end of the edge. |

---

### PrivateQuickbooksSyncStripePayout

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errors` | `[PrivateQuickbooksSyncError!]!` | - | - |
| `id` | `String!` | - | - |
| `refundNotices` | `[String!]!` | - | - |
| `status` | `QuickbooksSyncStatus!` | - | - |
| `stripePayoutAmount` | `Int!` | - | - |
| `stripePayoutCurrency` | `CoreCurrency!` | - | - |
| `stripePayoutDate` | `CoreDate!` | - | - |
| `stripePayoutId` | `String!` | - | - |

---

### PrivateQuickbooksSyncStripePayoutConnection

**Description:** The connection type for PrivateQuickbooksSyncStripePayout.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateQuickbooksSyncStripePayoutEdge]` | - | A list of edges. |
| `nodes` | `[PrivateQuickbooksSyncStripePayout]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateQuickbooksSyncStripePayoutEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateQuickbooksSyncStripePayout` | - | The item at the end of the edge. |

---

### PrivateRecommendation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dependentEstimateTierCount` | `Int!` | - | - |
| `explanation` | `I18nString!` | - | - |
| `id` | `String!` | - | - |
| `isArchived` | `Boolean!` | - | - |
| `name` | `I18nString!` | - | - |
| `type` | `RecommendationType!` | - | - |

---

### PrivateRemoteAccountingIntegration

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `quickbooksOnline` | `QuickBooksOnline!` | - | - |

---

### PrivateRemoteAccountingTaxMapping

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `externalTaxId` | `String!` | - | - |
| `id` | `String!` | - | - |
| `isCaZeroPctRate` | `Boolean!` | - | This is a flag indicates that this is that 0% tax rate to use for tips when syncing to QuickBooks Online.  This is only valid for Canadian companies. |
| `taxes` | `[PrivateTax!]!` | - | - |
| `type` | `RemoteAccountingType!` | - | - |

---

### PrivateRemoteCalendar

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `availabilityImpactHandling` | `AvailabilityImpactHandling!` | - | - |
| `calendarDisplayName` | `String` | - | - |
| `id` | `String` | - | - |
| `impactsAvailability` | `Boolean!` | - | - |
| `importAsBusy` | `Boolean!` | - | - |
| `isSyncInProgress` | `Boolean!` | - | - |
| `lastPolledAt` | `CoreDateTime` | - | - |
| `nextSyncAfter` | `CoreDateTime` | - | - |
| `remoteCalendarIntegration` | `PrivateRemoteCalendarIntegration!` | - | - |
| `remoteCalendarName` | `String` | - | - |
| `sharedCalendarUserName` | `String` | - | - |
| `sourceUrl` | `String` | - | - |
| `type` | `RemoteCalendarIntegrationType!` | - | - |
| `uniqueCalendarId` | `String` | - | - |

---

### PrivateRemoteCalendarIntegration

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allGoogleCalendars` | `[PrivateGoogleCalendar!]!` | - | - |
| `allRemoteCalendars` | `[PrivateRemoteCalendar!]!` | - | - |
| `id` | `String!` | - | - |
| `isLinked` | `Boolean!` | - | - |
| `linkedAccountEmail` | `String` | - | - |
| `name` | `String!` | - | - |
| `type` | `RemoteCalendarIntegrationType!` | - | - |

---

### PrivateRemoteQuickbooksAccount

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `accountNum` | `String` | - | User-defined account number to help the user in identifying the account within the chart-of-accounts and in deciding what should be posted to the account. |
| `accountSubType` | `String` | - | - |
| `accountType` | `String` | - | - |
| `description` | `String` | - | - |
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |

---

### PrivateRemoteTax

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `String` | - | - |
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |
| `rate` | `Int!` | - | - |

---

### PrivateRenameTagImpacts

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `combinedTagModelCount` | `Int!` | - | The resulting number of models that will have the new tag name. |
| `newTagModelCount` | `Int!` | - | The number of models that currently have the new tag name. |
| `originalTagModelCount` | `Int!` | - | The number of models that currently have the original tag name. |

---

### PrivateScheduledMessage

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `id` | `String!` | - | - |
| `language` | `String!` | - | - |
| `scheduledMessageTemplate` | `PrivateScheduledMessageTemplate` | - | - |
| `sendAt` | `CoreDateTime!` | - | - |
| `subject` | `String` | - | - |
| `template` | `String!` | - | - |
| `type` | `ScheduledMessageType!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateScheduledMessageConnection

**Description:** The connection type for PrivateScheduledMessage.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateScheduledMessageEdge]` | - | A list of edges. |
| `nodes` | `[PrivateScheduledMessage]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateScheduledMessageEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateScheduledMessage` | - | The item at the end of the edge. |

---

### PrivateScheduledMessageTemplate

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allScheduledMessages` | `PrivateScheduledMessageConnection` | after: String, before: String, first: Int, last: Int | - |
| `id` | `String!` | - | - |
| `name` | `I18nString` | - | - |
| `order` | `Int` | - | - |
| `subject` | `I18nString` | - | - |
| `template` | `I18nString` | - | - |
| `type` | `ScheduledMessageType` | - | - |

---

### PrivateScheduledMessageTemplateConnection

**Description:** The connection type for PrivateScheduledMessageTemplate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateScheduledMessageTemplateEdge]` | - | A list of edges. |
| `nodes` | `[PrivateScheduledMessageTemplate]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateScheduledMessageTemplateEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateScheduledMessageTemplate` | - | The item at the end of the edge. |

---

### PrivateSchedulerAvailability

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `adjustPreferredSlots` | `Boolean!` | - | Whether or not to adjust preferred slot times to account for travel time.  For example, if you have an open day, start your day at home at 9am, have preferred slot times of 9:30am and 11am, and you have a 45 minute travel to an appointment, the 9:30am preferred_slot time will be excluded as a possibility unless this setting is set to true, shifting the 9:30am preferred slot to 9:45am to account for the 45 minutes of travel time from your home. |
| `endDate` | `CoreDate` | - | - |
| `endOfDayLocation` | `PrivateSchedulerLocation!` | - | - |
| `endOfDayType` | `SchedulerEndOfDayType!` | - | - |
| `endTime` | `String!` | - | - |
| `excludeDates` | `[CoreDate!]!` | - | Dates to exclude from this availability that are exceptions to the recurrence rule. |
| `floatingDowntimeRules` | `[PrivateSchedulerFloatingDowntimeRule!]!` | - | - |
| `id` | `String!` | - | - |
| `includeDates` | `[CoreDate!]!` | - | Dates to include in this availability that are exceptions to the recurrence rule. |
| `isExclusive` | `Boolean!` | - | - |
| `maxAppointmentsPerDay` | `Int` | - | The maximum number of appointments that can be scheduled for this availability in a single day.  If null, there is no limit. |
| `name` | `String` | - | - |
| `preferredSlotPolicy` | `SchedulerPreferredSlotPolicy!` | - | - |
| `preferredSlotTimes` | `[String!]!` | - | The preferred slot times for this availability.  This is an array of times in HH:MM format. |
| `recurrenceRule` | `String` | - | - |
| `roundingMinutes` | `Int!` | - | The number of minutes to round slot start times to.  Can be 5, 10, 15, 30, or 60. |
| `serviceArea` | `PrivateSchedulerServiceArea!` | - | - |
| `startDate` | `CoreDate!` | - | - |
| `startOfDayLocation` | `PrivateSchedulerLocation!` | - | - |
| `startOfDayType` | `SchedulerStartOfDayType!` | - | - |
| `startTime` | `String!` | - | - |

---

### PrivateSchedulerCoordinates

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `latitude` | `String!` | - | - |
| `longitude` | `String!` | - | - |

---

### PrivateSchedulerFloatingDowntimeRule

**Description:** A floating downtime rule is a rule describes a period of time in which our scheduling system will make sure you have at a given amount of continuous downtime.  This could be useful to make sure you have a 30 minute period of time for lunch sometime between 11:00 and 13:30 for example.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `duration` | `Int!` | - | - |
| `endTime` | `String!` | - | The time of day at which this downtime rule ends.  This is a string in the format HH:MM. |
| `id` | `String!` | - | - |
| `startTime` | `String!` | - | The time of day at which this downtime rule starts.  This is a string in the format HH:MM. |

---

### PrivateSchedulerLocation

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `addressLine` | `String` | - | - |
| `coordinates` | `PrivateSchedulerCoordinates` | - | - |
| `id` | `String!` | - | - |
| `manualLat` | `String` | - | The geocoded latitude of the location. |
| `manualLng` | `String` | - | The geocoded longitude of the location. |
| `type` | `SchedulerLocationType!` | - | - |
| `what3words` | `PrivateSchedulerWhat3words` | - | - |

---

### PrivateSchedulerPolygonParameter

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `shapes` | `[PrivateSchedulerShape!]!` | - | - |

---

### PrivateSchedulerRadialParameter

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `center` | `PrivateSchedulerLocation!` | - | - |
| `id` | `String!` | - | - |
| `travelTime` | `Int!` | - | - |

---

### PrivateSchedulerSelfScheduleMaxTravelTime

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `daysFromToday` | `Int!` | - | - |
| `maxTravelTime` | `Int!` | - | - |

---

### PrivateSchedulerServiceArea

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `algorithm` | `SchedulerServiceAreaAlgorithmType!` | - | - |
| `buffer` | `Int!` | - | - |
| `id` | `String!` | - | - |
| `includeTraffic` | `Boolean!` | - | - |
| `invalidAddressTravelTime` | `Int!` | - | The number of minutes to use for the travel time if an address is invalid. |
| `isSelfSchedulable` | `Boolean!` | - | - |
| `maxGoodTravelTimeMinutes` | `Int!` | - | The maximum number of minutes to consider a travel time as 'good'. |
| `name` | `String!` | - | - |
| `openDayWeight` | `Int!` | - | - |
| `outsideServiceAreaMinutes` | `Int!` | - | - |
| `polygonParameter` | `PrivateSchedulerPolygonParameter` | - | - |
| `radialParameter` | `PrivateSchedulerRadialParameter` | - | - |
| `routingPreference` | `SchedulerRoutingPreferenceType!` | - | - |
| `selfScheduleMaxTravelTimes` | `[PrivateSchedulerSelfScheduleMaxTravelTime!]!` | - | - |
| `travelMode` | `SchedulerTravelMode!` | - | - |
| `user` | `PrivateUser!` | - | - |

---

### PrivateSchedulerShape

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `circleCenter` | `PrivateSchedulerCoordinates` | - | - |
| `circleRadius` | `Float` | - | - |
| `circleRadiusUnit` | `SchedulerDistanceUnitType` | - | - |
| `id` | `String!` | - | - |
| `inclusionMethod` | `SchedulerShapeInclusionMethod!` | - | Whether the shape defines an area to be included or excluded from a service area. |
| `name` | `String` | - | - |
| `polygonPoints` | `[PrivateSchedulerCoordinates!]` | - | - |
| `shape` | `String` | - | - |
| `type` | `SchedulerShapeType!` | - | - |

---

### PrivateSchedulerV2SearchResultsWrapper

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errors` | `[String!]!` | - | - |
| `results` | `[PrivateV2SchedulerSearchResults!]!` | - | - |

---

### PrivateSchedulerV2Slot

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `afterTrafficMinutes` | `Int` | - | - |
| `afterTravelMinutes` | `Int` | - | - |
| `audit` | `[PrivateSchedulerV2SlotAudit!]` | - | - |
| `availabilityId` | `String` | - | The ID of the availability that this slot was generated from. |
| `beforeTrafficMinutes` | `Int` | - | - |
| `beforeTravelMinutes` | `Int` | - | - |
| `buffer` | `Int` | - | - |
| `duration` | `Int!` | - | - |
| `filteredReasons` | `[SchedulerSlotFilterReasonType!]!` | - | - |
| `flags` | `[SchedulerSlotFlagType!]!` | - | - |
| `isAPreferredSlot` | `Boolean` | - | This slot represents one of the preferred slot times configured in the technician's availability settings. |
| `latitude` | `String` | - | - |
| `longitude` | `String` | - | - |
| `outsideServiceAreaMiles` | `Int` | - | - |
| `outsideServiceAreaMinutes` | `Int` | - | - |
| `startsAt` | `CoreDateTime!` | - | - |
| `technicianId` | `String!` | - | - |
| `timezone` | `String!` | - | - |
| `travelMode` | `SchedulerTravelMode!` | - | - |
| `weight` | `Float!` | - | - |

---

### PrivateSchedulerV2SlotAudit

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `String!` | - | - |
| `metadata` | `JSON` | - | - |

---

### PrivateSchedulerWhat3words

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `latitude` | `String!` | - | - |
| `longitude` | `String!` | - | - |
| `what3words` | `String!` | - | - |

---

### PrivateSentOrScheduledMessage

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `deliveryType` | `SentOrScheduledMessageDeliveryType!` | - | - |
| `id` | `String!` | - | - |
| `recipientName` | `String` | - | - |
| `relatedId` | `String!` | - | - |
| `relatedType` | `SentOrScheduledMessageRelatedType!` | - | - |
| `sentOrScheduledAt` | `CoreDateTime!` | - | - |
| `shortSummary` | `String!` | - | - |
| `status` | `SentOrScheduledMessageStatus!` | - | - |
| `type` | `SentOrScheduledMessageType!` | - | - |

---

### PrivateSentOrScheduledMessageConnection

**Description:** The connection type for PrivateSentOrScheduledMessage.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateSentOrScheduledMessageEdge]` | - | A list of edges. |
| `nodes` | `[PrivateSentOrScheduledMessage]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateSentOrScheduledMessageEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateSentOrScheduledMessage` | - | The item at the end of the edge. |

---

### PrivateServiceLibraryGroup

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `allServiceLibraryItems` | `[PrivateServiceLibraryItem!]!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `id` | `String!` | - | - |
| `isMultiChoice` | `Boolean!` | - | - |
| `name` | `I18nString!` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |

---

### PrivateServiceLibraryItem

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `description` | `I18nString!` | - | - |
| `duration` | `Int` | - | - |
| `educationDescription` | `I18nString!` | - | - |
| `id` | `String!` | - | - |
| `isTuning` | `Boolean` | - | - |
| `name` | `I18nString!` | - | - |
| `sequenceNumber` | `Int!` | - | - |
| `serviceLibraryGroup` | `PrivateServiceLibraryGroup!` | - | - |
| `type` | `MasterServiceItemType!` | - | - |

---

### PrivateServiceLibraryItemConnection

**Description:** The connection type for PrivateServiceLibraryItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateServiceLibraryItemEdge]` | - | A list of edges. |
| `nodes` | `[PrivateServiceLibraryItem]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateServiceLibraryItemEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateServiceLibraryItem` | - | The item at the end of the edge. |

---

### PrivateSharedCalendar

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `createdAt` | `CoreDateTime` | - | - |
| `eventTypesToShare` | `[EventType!]!` | - | - |
| `hasBeenAccepted` | `Boolean!` | - | When sending a shared calendar invitation email, this will be false until the recipient has accepted the invitation.  If the shared calendar was linked via direct authentication this will always return true. |
| `id` | `String!` | - | - |
| `includeClientPianoDetails` | `Boolean!` | - | - |
| `remoteCalendarCompanyName` | `String` | - | - |
| `remoteCalendarUserName` | `String` | - | - |
| `sharedToEmailAddress` | `String` | - | - |
| `showEventDetails` | `Boolean!` | - | - |

---

### PrivateSkipStripePayout

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `id` | `String!` | - | - |
| `reasonGiven` | `String` | - | - |
| `skippedAt` | `CoreDateTime!` | - | - |
| `skippedBy` | `PrivateUser!` | - | - |
| `stripePayoutAmount` | `Int!` | - | - |
| `stripePayoutCreatedAt` | `CoreDateTime!` | - | - |
| `stripePayoutCurrency` | `String!` | - | - |
| `stripePayoutError` | `String` | - | - |
| `stripePayoutId` | `String!` | - | - |

---

### PrivateSmsMessage

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `contact` | `PrivateContact` | - | - |
| `createdAt` | `CoreDateTime` | - | - |
| `id` | `String!` | - | - |
| `message` | `String!` | - | - |
| `phoneNumber` | `String` | format: PhoneFormat | - |
| `status` | `SmsStatus` | - | - |
| `updatedAt` | `CoreDateTime` | - | - |

---

### PrivateStripePaymentProcessing

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `businessName` | `String` | - | - |
| `chargesEnabled` | `Boolean` | - | - |
| `country` | `String` | - | - |
| `defaultCurrency` | `CoreCurrency` | - | - |
| `detailsSubmitted` | `Boolean` | - | - |
| `hasGazelleAsStripeDisplayName` | `Boolean` | - | This will return true if the account's dashboard has Gazelle as the display name. |
| `isConnected` | `Boolean!` | - | - |
| `payoutsEnabled` | `Boolean` | - | - |
| `primaryUserEmail` | `String` | - | - |
| `stripeAccountLinkUrl` | `String` | - | - |
| `stripePaymentMethodStatuses` | `StripePaymentMethodStatus!` | - | - |
| `verificationIsWaitingOnOwner` | `Boolean` | - | This will return true of there are account verification steps that are waiting on the Stripe account owner to complete. |
| `verificationIsWaitingOnStripe` | `Boolean` | - | This will return true of there are account verification steps that are waiting on Stripe to complete. |

---

### PrivateSystemNotification

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `alertType` | `SystemNotificationAlertType!` | - | - |
| `client` | `PrivateClient` | - | - |
| `estimate` | `PrivateEstimate` | - | - |
| `groupingToken` | `String!` | - | - |
| `id` | `String!` | - | - |
| `invoice` | `PrivateInvoice` | - | - |
| `isDismissable` | `Boolean!` | - | - |
| `message` | `String!` | - | - |
| `piano` | `PrivatePiano` | - | - |
| `referenceData` | `String` | - | This is JSON data that might hold additional information used for deep linking.  For example a url to the calendar integration settings that triggered this notification. |
| `subType` | `SystemNotificationSubType` | - | - |
| `type` | `SystemNotificationType!` | - | - |
| `user` | `PrivateUser!` | - | - |

---

### PrivateSystemNotificationConnection

**Description:** The connection type for PrivateSystemNotification.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateSystemNotificationEdge]` | - | A list of edges. |
| `nodes` | `[PrivateSystemNotification]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateSystemNotificationEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateSystemNotification` | - | The item at the end of the edge. |

---

### PrivateTax

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `activeOrHistorical` | `ActiveOrHistorical` | - | - |
| `default` | `Boolean` | - | - |
| `id` | `String!` | - | - |
| `name` | `String!` | - | - |
| `rate` | `Int!` | - | - |
| `sampleInvoices` | `[PrivateInvoice!]!` | - | A list of up to 5 invoices that use this tax. |

---

### PrivateTemplatePreview

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `error` | `String` | - | - |
| `message` | `String` | - | - |
| `subject` | `String` | - | - |

---

### PrivateTimelineEntry

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `alertType` | `SystemNotificationAlertType` | - | - |
| `appointment` | `PrivateEvent` | - | - |
| `client` | `PrivateClient!` | - | - |
| `comment` | `String` | - | - |
| `duration` | `Int` | - | - |
| `emailFailureReason` | `String` | - | - |
| `emailRecipientName` | `String` | - | - |
| `emailStatus` | `EmailStatus` | - | - |
| `estimate` | `PrivateEstimate` | - | - |
| `id` | `String!` | - | - |
| `invoice` | `PrivateInvoice` | - | - |
| `invoicePayment` | `PrivateInvoicePayment` | - | - |
| `occurredAt` | `CoreDateTime!` | - | - |
| `piano` | `PrivatePiano` | - | - |
| `relatedId` | `String` | - | - |
| `relatedType` | `String` | - | - |
| `smsStatus` | `EmailStatus` | - | - |
| `summary` | `String` | - | - |
| `type` | `TimelineEntryType!` | - | - |
| `user` | `PrivateUser` | - | - |

---

### PrivateTimelineEntryConnection

**Description:** The connection type for PrivateTimelineEntry.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateTimelineEntryEdge]` | - | A list of edges. |
| `nodes` | `[PrivateTimelineEntry]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateTimelineEntryEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateTimelineEntry` | - | The item at the end of the edge. |

---

### PrivateTravelTimes

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `errorMessage` | `String` | - | - |
| `errorType` | `DriveTimeErrorType` | - | - |
| `id` | `String` | - | - |
| `secondsWithTraffic` | `Int` | - | - |
| `secondsWithoutTraffic` | `Int` | - | - |

---

### PrivateUpcomingJakklopsBillingInvoiceLine

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `amount` | `Int!` | - | - |
| `description` | `String!` | - | - |
| `id` | `String!` | - | - |

---

### PrivateUpcomingLifecycleReminder

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientsReceivingMultiple` | `Int!` | - | The number of clients receiving multiple reminders in the next 72 hours |
| `typeAndStateSummary` | `[LifecycleTypeAndStateSummary!]!` | - | - |

---

### PrivateUpcomingMaintenanceNotice

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `message` | `String!` | - | - |
| `startsAt` | `CoreDateTime!` | - | - |

---

### PrivateUser

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `accessLevel` | `AccessLevel` | - | - |
| `authorizedIntegrations` | `[PrivateAuthorizedIntegration!]!` | - | This is a list of all the applications that have been authorized by this User to access the Gazelle account.  This is only available to API requests authenticated with full admin access. |
| `calendarDefaultSendAppointmentConfirmation` | `Boolean!` | - | - |
| `calendarDefaultShowAvailability` | `Boolean!` | - | - |
| `calendarDefaultShowConfirmationWarnings` | `Boolean!` | - | - |
| `calendarDefaultTitleMode` | `CalendarTitleMode!` | - | - |
| `calendarDefaultUserId` | `String` | - | - |
| `calendarDefaultView` | `JSON!` | - | - |
| `calendarDefaultViewType` | `CalendarViewType!` | - | - |
| `calendarFontSize` | `CalendarFontSize!` | - | - |
| `calendarIcsExportEventTypes` | `[EventType!]!` | - | - |
| `calendarMakeCompletedAndPastEventsDimmer` | `Boolean!` | - | - |
| `calendarPromptToScheduleAfterCompletion` | `Boolean!` | - | - |
| `calendarShowCanceledAppointments` | `Boolean!` | - | - |
| `calendarShowDetailsOnIcsExport` | `Boolean!` | - | - |
| `calendarShowNonschedulableUsers` | `Boolean!` | - | - |
| `canViewCompanyMetrics` | `Boolean!` | - | - |
| `clientLocalization` | `CoreLocalization` | - | This will be null if no client localization override has been set for this user. If it is set, then this localization will be the default for any clients where this user is their preferred technician (unless the client has a localization override set). |
| `color` | `String!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `defaultBuffer` | `Int!` | - | - |
| `defaultClientLocalization` | `CoreLocalization!` | - | This is the localization to be used for any clients where this user is the preferred technician (unless the specific client has a localization override).  You should use this instead of clientLocalization because this one can never be null.  This will return clientLocalization, or if that is null it will return the company's defaultClientLocalization. |
| `defaultUserLocalization` | `CoreLocalization!` | - | This is the localization to be used for displaying things to a user.  You should query this instead of localization because localization may be null.  This defaultUserLocalization field falls through to the company default setting.  This will never be null and should always be the localization to use for displaying things to the user. |
| `email` | `String!` | - | - |
| `firstName` | `String!` | - | - |
| `flags` | `PrivateUserFlags!` | - | - |
| `fullName` | `String` | - | Full name of the user |
| `genericReferralUrl` | `String!` | - | - |
| `hasLimitedAccess` | `Boolean` | - | - |
| `id` | `String!` | - | - |
| `intercomUserHash` | `String!` | - | A hash used to verify the identity of this user with the Intercom Messenger component |
| `isSchedulable` | `Boolean` | - | - |
| `isTrafficEnabled` | `Boolean!` | - | - |
| `lastName` | `String!` | - | - |
| `localization` | `CoreLocalization` | - | This will be null if no localization override has been set for this user. If it is set, this is the localization override (overridden from the company default user localization).  You most likely do not want to use this, but instead should use defaultUserLocalization. |
| `region` | `String` | - | - |
| `reservationNotificationsForAllUsers` | `Boolean!` | - | - |
| `reservationNotificationsForSpecificUsers` | `PrivateUserConnection!` | after: String, before: String, first: Int, last: Int | - |
| `schedulerSettings` | `PrivateUserSchedulerSettings` | - | - |
| `sharedCalendarToken` | `String` | - | - |
| `sharedCalendars` | `[PrivateSharedCalendar!]!` | - | - |
| `status` | `UserStatus!` | - | - |
| `timezone` | `String!` | - | - |
| `uiExpandedTimeline` | `Boolean!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |
| `wantsReservationNotifications` | `Boolean!` | - | - |

---

### PrivateUserConnection

**Description:** The connection type for PrivateUser.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `edges` | `[PrivateUserEdge]` | - | A list of edges. |
| `nodes` | `[PrivateUser]` | - | A list of nodes. |
| `pageInfo` | `PageInfo!` | - | Information to aid in pagination. |
| `totalCount` | `Int!` | - | - |

---

### PrivateUserEdge

**Description:** An edge in a connection.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `cursor` | `String!` | - | A cursor for use in pagination. |
| `node` | `PrivateUser` | - | The item at the end of the edge. |

---

### PrivateUserFlags

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `hideDashboardReferralNotice` | `Boolean` | - | - |
| `hideDesktopCalendarWhatsNew` | `Boolean` | - | - |
| `makeMePreferredTechForNewClients` | `Boolean` | - | - |
| `uiv2Allowed` | `Boolean!` | - | - |
| `uiv2Enabled` | `Boolean!` | - | - |
| `uiv2Enforced` | `Boolean!` | - | - |

---

### PrivateUserSchedulerSettings

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `defaultTravelMode` | `SchedulerTravelMode!` | - | - |
| `id` | `String!` | - | - |
| `longTermLimitDays` | `Int!` | - | - |
| `longTermLimitMessage` | `I18nString!` | - | - |
| `shortTermLimitHours` | `Int!` | - | - |
| `shortTermLimitHoursType` | `PrivateSchedulerShortTermLimitHoursType!` | - | - |
| `shortTermLimitMessage` | `I18nString!` | - | - |

---

### PrivateUserWithApiKey

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `accessLevel` | `AccessLevel` | - | - |
| `apiKey` | `String!` | - | - |
| `authorizedIntegrations` | `[PrivateAuthorizedIntegration!]!` | - | This is a list of all the applications that have been authorized by this User to access the Gazelle account.  This is only available to API requests authenticated with full admin access. |
| `calendarDefaultSendAppointmentConfirmation` | `Boolean!` | - | - |
| `calendarDefaultShowAvailability` | `Boolean!` | - | - |
| `calendarDefaultShowConfirmationWarnings` | `Boolean!` | - | - |
| `calendarDefaultTitleMode` | `CalendarTitleMode!` | - | - |
| `calendarDefaultUserId` | `String` | - | - |
| `calendarDefaultView` | `JSON!` | - | - |
| `calendarDefaultViewType` | `CalendarViewType!` | - | - |
| `calendarFontSize` | `CalendarFontSize!` | - | - |
| `calendarIcsExportEventTypes` | `[EventType!]!` | - | - |
| `calendarMakeCompletedAndPastEventsDimmer` | `Boolean!` | - | - |
| `calendarPromptToScheduleAfterCompletion` | `Boolean!` | - | - |
| `calendarShowCanceledAppointments` | `Boolean!` | - | - |
| `calendarShowDetailsOnIcsExport` | `Boolean!` | - | - |
| `calendarShowNonschedulableUsers` | `Boolean!` | - | - |
| `canViewCompanyMetrics` | `Boolean!` | - | - |
| `clientLocalization` | `CoreLocalization` | - | This will be null if no client localization override has been set for this user. If it is set, then this localization will be the default for any clients where this user is their preferred technician (unless the client has a localization override set). |
| `color` | `String!` | - | - |
| `createdAt` | `CoreDateTime!` | - | - |
| `defaultBuffer` | `Int!` | - | - |
| `defaultClientLocalization` | `CoreLocalization!` | - | This is the localization to be used for any clients where this user is the preferred technician (unless the specific client has a localization override).  You should use this instead of clientLocalization because this one can never be null.  This will return clientLocalization, or if that is null it will return the company's defaultClientLocalization. |
| `defaultUserLocalization` | `CoreLocalization!` | - | This is the localization to be used for displaying things to a user.  You should query this instead of localization because localization may be null.  This defaultUserLocalization field falls through to the company default setting.  This will never be null and should always be the localization to use for displaying things to the user. |
| `email` | `String!` | - | - |
| `firstName` | `String!` | - | - |
| `flags` | `PrivateUserFlags!` | - | - |
| `fullName` | `String` | - | Full name of the user |
| `genericReferralUrl` | `String!` | - | - |
| `hasLimitedAccess` | `Boolean` | - | - |
| `id` | `String!` | - | - |
| `intercomUserHash` | `String!` | - | A hash used to verify the identity of this user with the Intercom Messenger component |
| `isSchedulable` | `Boolean` | - | - |
| `isTrafficEnabled` | `Boolean!` | - | - |
| `lastName` | `String!` | - | - |
| `localization` | `CoreLocalization` | - | This will be null if no localization override has been set for this user. If it is set, this is the localization override (overridden from the company default user localization).  You most likely do not want to use this, but instead should use defaultUserLocalization. |
| `region` | `String` | - | - |
| `reservationNotificationsForAllUsers` | `Boolean!` | - | - |
| `reservationNotificationsForSpecificUsers` | `PrivateUserConnection!` | after: String, before: String, first: Int, last: Int | - |
| `schedulerSettings` | `PrivateUserSchedulerSettings` | - | - |
| `sharedCalendarToken` | `String` | - | - |
| `sharedCalendars` | `[PrivateSharedCalendar!]!` | - | - |
| `status` | `UserStatus!` | - | - |
| `timezone` | `String!` | - | - |
| `uiExpandedTimeline` | `Boolean!` | - | - |
| `updatedAt` | `CoreDateTime!` | - | - |
| `wantsReservationNotifications` | `Boolean!` | - | - |

---

### PrivateV2SchedulerSearchResults

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `slots` | `[PrivateSchedulerV2Slot!]!` | - | - |
| `technicianSearchSignature` | `String!` | - | - |

---

### PrivateValidatePhoneNumberResponse

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `phoneNumber` | `String` | format: PhoneFormat | - |

---

### QuickBooksOnline

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `companyName` | `String` | - | - |
| `isClassTrackingEnabled` | `Boolean` | - | - |
| `isConnected` | `Boolean!` | - | This will actively exercise the QuickBooks Online API to verify that the integration is connected.  This API call can take a second or two, depending on the QuickBooks Online API response time. |
| `isConnectedPassive` | `Boolean!` | - | This will check if Gazelle has information about an authenticated QuickBooks Online integration, but it will not test the QuickBooks Online API to verify that QBO is accessible.  This is useful if you need a fast way to check if the QuickBooks Online integration is available. |

---

### RecordCallCenterContactPayload

**Description:** Autogenerated return type of RecordCallCenterContact.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientLog` | `PrivateClientLog` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean!` | - | - |

---

### RemoveCompanyLogoPayload

**Description:** Autogenerated return type of RemoveCompanyLogo.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### RemoveFeatureTrialFromSubscriptionPayload

**Description:** Autogenerated return type of RemoveFeatureTrialFromSubscription.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### RenameTagPayload

**Description:** Autogenerated return type of RenameTag.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `tags` | `[String!]` | - | - |

---

### ResendSharedCalendarTokenPayload

**Description:** Autogenerated return type of ResendSharedCalendarToken.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### RevokeAuthorizedIntegrationPayload

**Description:** Autogenerated return type of RevokeAuthorizedIntegration.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SchedulerV2RecordSelectedSlotPayload

**Description:** Autogenerated return type of SchedulerV2RecordSelectedSlot.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SchedulerV2SearchPayload

**Description:** Autogenerated return type of SchedulerV2Search.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `searchId` | `String` | - | - |
| `technicianSearchSignatures` | `[String!]` | - | - |
| `warnings` | `[String!]` | - | - |

---

### SendCalendarShareInstructionsPayload

**Description:** Autogenerated return type of SendCalendarShareInstructions.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SendEstimateEmailPayload

**Description:** Autogenerated return type of SendEstimateEmail.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `message` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SendInvoiceEmailPayload

**Description:** Autogenerated return type of SendInvoiceEmail.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `message` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SendReferralPayload

**Description:** Autogenerated return type of SendReferral.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `message` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SendSchedulerV2FeedbackPayload

**Description:** Autogenerated return type of SendSchedulerV2Feedback.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean!` | - | - |

---

### SetCanadianZeroPercentTaxRatePayload

**Description:** Autogenerated return type of SetCanadianZeroPercentTaxRate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteAccountingTaxMapping` | `PrivateRemoteAccountingTaxMapping` | - | - |

---

### SignLegalContractPayload

**Description:** Autogenerated return type of SignLegalContract.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### SignupPayload

**Description:** Autogenerated return type of Signup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `companyId` | `String` | - | - |
| `companyWebsite` | `String` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `userApiKey` | `String` | - | - |
| `userId` | `String` | - | - |

---

### StartFeatureTrialPayload

**Description:** Autogenerated return type of StartFeatureTrial.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### StripeAddress

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `countryCode` | `String` | - | - |
| `line1` | `String` | - | - |
| `line2` | `String` | - | - |
| `municipality` | `String` | - | - |
| `postalCode` | `String` | - | - |
| `region` | `String` | - | - |

---

### StripeCustomerTaxId

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `type` | `String!` | - | - |
| `value` | `String!` | - | - |

---

### StripePaymentMethodStatus

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `isBancontactActive` | `Boolean` | - | - |
| `isCardActive` | `Boolean` | - | - |
| `isEpsActive` | `Boolean` | - | - |
| `isGiropayActive` | `Boolean` | - | - |
| `isIdealActive` | `Boolean` | - | - |
| `isP24Active` | `Boolean` | - | - |
| `isSepaActive` | `Boolean` | - | - |
| `isSofortActive` | `Boolean` | - | - |

---

### SyncRemoteCalendarPayload

**Description:** Autogenerated return type of SyncRemoteCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `success` | `Boolean` | - | - |

---

### ToggleSharedCalendarPayload

**Description:** Autogenerated return type of ToggleSharedCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `user` | `PrivateUser` | - | - |

---

### UncancelEventPayload

**Description:** Autogenerated return type of UncancelEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UncompleteEventPayload

**Description:** Autogenerated return type of UncompleteEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UnconfirmEventPayload

**Description:** Autogenerated return type of UnconfirmEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateBulkActionPayload

**Description:** Autogenerated return type of UpdateBulkAction.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `bulkAction` | `PrivateBulkAction` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateClientLogPayload

**Description:** Autogenerated return type of UpdateClientLog.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `clientLog` | `PrivateClientLog` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateClientPayload

**Description:** Autogenerated return type of UpdateClient.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateCompanyFeatureTogglesPayload

**Description:** Autogenerated return type of UpdateCompanyFeatureToggles.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `company` | `PrivateCompany` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateCompanySettingsPayload

**Description:** Autogenerated return type of UpdateCompanySettings.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `company` | `PrivateCompany` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateContactAddressPayload

**Description:** Autogenerated return type of UpdateContactAddress.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `address` | `PrivateContactAddress` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateContactEmailPayload

**Description:** Autogenerated return type of UpdateContactEmail.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `email` | `PrivateContactEmail` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateContactLocationPayload

**Description:** Autogenerated return type of UpdateContactLocation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `location` | `PrivateContactLocation` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateContactPayload

**Description:** Autogenerated return type of UpdateContact.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `contact` | `PrivateContact` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateContactPhonePayload

**Description:** Autogenerated return type of UpdateContactPhone.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `phone` | `PrivateContactPhone` | - | - |

---

### UpdateContactsSortOrderPayload

**Description:** Autogenerated return type of UpdateContactsSortOrder.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `client` | `PrivateClient` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateEstimateChecklistGroupPayload

**Description:** Autogenerated return type of UpdateEstimateChecklistGroup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateChecklistGroup` | `PrivateEstimateChecklistGroup` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateEstimateChecklistItemPayload

**Description:** Autogenerated return type of UpdateEstimateChecklistItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateChecklistItem` | `PrivateEstimateChecklistItem` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateEstimateChecklistPayload

**Description:** Autogenerated return type of UpdateEstimateChecklist.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimateChecklist` | `PrivateEstimateChecklist` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateEstimatePayload

**Description:** Autogenerated return type of UpdateEstimate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `estimate` | `PrivateEstimate` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateEventCancelNoticePayload

**Description:** Autogenerated return type of UpdateEventCancelNotice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `eventCancelNotice` | `PrivateEventCancelNotice` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateEventPayload

**Description:** Autogenerated return type of UpdateEvent.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `badgeCount` | `PrivateBadgeCount` | - | - |
| `event` | `PrivateEvent` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateInvoicePayload

**Description:** Autogenerated return type of UpdateInvoice.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `invoice` | `PrivateInvoice` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateInvoicePaymentPayload

**Description:** Autogenerated return type of UpdateInvoicePayment.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `invoicePayment` | `PrivateInvoicePayment` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateLocalizationPayload

**Description:** Autogenerated return type of UpdateLocalization.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `localization` | `CoreLocalization` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateMasterServiceGroupPayload

**Description:** Autogenerated return type of UpdateMasterServiceGroup.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `masterServiceGroup` | `PrivateMasterServiceGroup` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateMasterServiceItemPayload

**Description:** Autogenerated return type of UpdateMasterServiceItem.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `masterServiceItem` | `PrivateMasterServiceItem` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateOnboardingPayload

**Description:** Autogenerated return type of UpdateOnboarding.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `onboarding` | `PrivateOnboarding!` | - | - |

---

### UpdateOnboardingStepPayload

**Description:** Autogenerated return type of UpdateOnboardingStep.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `dismissed` | `Boolean!` | - | - |
| `id` | `String!` | - | Calling this an id so Apollo GraphQL can cache it effectively. |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdatePianoMeasurementPayload

**Description:** Autogenerated return type of UpdatePianoMeasurement.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `pianoMeasurement` | `PrivatePianoMeasurement` | - | - |

---

### UpdatePianoPayload

**Description:** Autogenerated return type of UpdatePiano.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `piano` | `PrivatePiano` | - | - |

---

### UpdatePianoPhotoPayload

**Description:** Autogenerated return type of UpdatePianoPhoto.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `pianoPhoto` | `PrivatePianoPhoto` | - | - |

---

### UpdateQuickbooksAccountMappingPayload

**Description:** Autogenerated return type of UpdateQuickbooksAccountMapping.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `quickbooksAccountMapping` | `PrivateQuickbooksAccountMapping` | - | - |

---

### UpdateRecommendationPayload

**Description:** Autogenerated return type of UpdateRecommendation.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `recommendation` | `PrivateRecommendation` | - | - |

---

### UpdateRemoteAccountingTaxMappingPayload

**Description:** Autogenerated return type of UpdateRemoteAccountingTaxMapping.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteAccountingTaxMapping` | `PrivateRemoteAccountingTaxMapping` | - | - |

---

### UpdateRemoteCalendarIntegrationPayload

**Description:** Autogenerated return type of UpdateRemoteCalendarIntegration.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteCalendarIntegration` | `PrivateRemoteCalendarIntegration` | - | - |

---

### UpdateRemoteCalendarPayload

**Description:** Autogenerated return type of UpdateRemoteCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `remoteCalendar` | `PrivateRemoteCalendar` | - | - |

---

### UpdateScheduledMessagePayload

**Description:** Autogenerated return type of UpdateScheduledMessage.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `scheduledMessage` | `PrivateScheduledMessage` | - | - |

---

### UpdateScheduledMessageTemplatePayload

**Description:** Autogenerated return type of UpdateScheduledMessageTemplate.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `scheduledMessageTemplate` | `PrivateScheduledMessageTemplate` | - | - |

---

### UpdateSchedulerAvailabilityPayload

**Description:** Autogenerated return type of UpdateSchedulerAvailability.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `availability` | `PrivateSchedulerAvailability` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateSchedulerServiceAreaPayload

**Description:** Autogenerated return type of UpdateSchedulerServiceArea.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `serviceArea` | `PrivateSchedulerServiceArea` | - | - |

---

### UpdateSharedCalendarPayload

**Description:** Autogenerated return type of UpdateSharedCalendar.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `sharedCalendar` | `PrivateSharedCalendar` | - | - |

---

### UpdateTaxPayload

**Description:** Autogenerated return type of UpdateTax.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `tax` | `PrivateTax` | - | - |

---

### UpdateUserFlagsPayload

**Description:** Autogenerated return type of UpdateUserFlags.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `flags` | `PrivateUserFlags` | - | - |
| `mutationErrors` | `[CoreFieldError!]!` | - | - |

---

### UpdateUserPayload

**Description:** Autogenerated return type of UpdateUser.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `user` | `PrivateUser` | - | - |

---

### UpdateUserSettingsPayload

**Description:** Autogenerated return type of UpdateUserSettings.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `user` | `PrivateUser` | - | - |

---

### ValidatePhoneNumberPayload

**Description:** Autogenerated return type of ValidatePhoneNumber.

**Champs:**

| Nom | Type | Arguments | Description |
|-----|------|-----------|-------------|
| `mutationErrors` | `[CoreFieldError!]!` | - | - |
| `response` | `PrivateValidatePhoneNumberResponse` | - | - |

---

## Types Input

### ChangeMasterServiceListPricesInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `itemType` | `MasterServiceItemType` | None | - |
| `groupId` | `String` | None | - |
| `changeMethod` | `ChangeMethod!` | None | - |
| `amount` | `Int!` | None | The amount to change... |

---

### I18nStringInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `da_DK` | `String` | None | - |
| `de_DE` | `String` | None | - |
| `en_US` | `String` | None | - |
| `en_NZ` | `String` | None | - |
| `en_GB` | `String` | None | - |
| `en_AU` | `String` | None | - |
| `en_CA` | `String` | None | - |
| `es_US` | `String` | None | - |
| `es_MX` | `String` | None | - |
| `es_CL` | `String` | None | - |
| `el_GR` | `String` | None | - |
| `fr_CA` | `String` | None | - |
| `fr_FR` | `String` | None | - |
| `it_IT` | `String` | None | - |
| `ja_JP` | `String` | None | - |
| `nb_NO` | `String` | None | - |
| `nl_NL` | `String` | None | - |
| `pl_PL` | `String` | None | - |
| `zh_CN` | `String` | None | - |
| `zh_TW` | `String` | None | - |

---

### ImportServiceLibraryItemsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `serviceLibraryGroupId` | `String!` | None | - |
| `matchGroupNameWithLocale` | `String!` | None | - |
| `serviceLibraryItemIds` | `[String!]!` | None | - |

---

### NullableFilterStringInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `value` | `String` | None | - |

---

### PaymentMethodFilterInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `stripePaymentMethod` | `[StripePaymentMethods!]` | None | - |
| `invoicePaymentType` | `[InvoicePaymentType!]` | None | - |
| `quickbooksPaymentType` | `[InvoicePaymentType!]` | None | - |

---

### PrivateAllCallCenterItemsFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `search` | `String` | None | - |
| `referenceType` | `[CallCenterReferenceType!]` | None | Filter by reference type (scheduled message, lifecycle, or both) |
| `lifecycleState` | `[LifecycleState!]` | None | Filter by lifecycle state |
| `lifecycleIds` | `[String!]` | None | Filter by the lifecycle that the client is assigned to. |
| `onlyDue` | `Boolean` | None | Filter to show only overdue items (defaults to true) |

---

### PrivateAllClientsFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `search` | `String` | None | - |
| `status` | `[ClientStatus!]` | None | - |
| `clientType` | `[String!]` | None | - |
| `preferredTechnicianIds` | `[NullableFilterStringInput!]` | None | - |
| `preferredTechnicianId` | `[String!]` | None | - |
| `isPaused` | `Boolean` | None | - |
| `hasBadAddress` | `Boolean` | None | - |
| `lifecycleIds` | `[NullableFilterStringInput!]` | None | Filter clients by the reminder that the client is assigned to.  To filter for clients that are not assigned to a reminder send a NullableFilterStringInput value of null. |
| `hasTimelineActivityGet` | `CoreDate` | None | Filter for clients with timeline activity after or on a date. |
| `hasTimelineActivityLet` | `CoreDate` | None | Filter for clients with timeline activity before or on a date. |
| `hasNoTimelineActivityGet` | `CoreDate` | None | Filter for clients with NO timeline activity after or on a date. |
| `hasNoTimelineActivityLet` | `CoreDate` | None | Filter for clients with NO timeline activity before or on a date. |
| `hasAppointmentGet` | `CoreDate` | None | Filter for clients with a non canceled appointment after or on a date. |
| `hasAppointmentLet` | `CoreDate` | None | Filter for clients with a non canceled appointment before or on a date. |
| `hasTuningAppointmentGet` | `CoreDate` | None | Filter for clients with a non canceled, tuning appointment after or on a date. |
| `hasTuningAppointmentLet` | `CoreDate` | None | Filter for clients with a non canceled, tuning appointment before or on a date. |
| `hasPastAppointmentScheduled` | `Boolean` | None | Filter clients that do or do not have a past appointment. |
| `hasFutureAppointmentScheduled` | `Boolean` | None | Filter clients that do or do not have a future appointment scheduled. |
| `hasPianoLastTunedGet` | `CoreDate` | None | Filter for clients with a piano that was last tuned after or on a date. |
| `hasPianoLastTunedLet` | `CoreDate` | None | Filter for clients with a piano that was last tuned before or on a date. |
| `createdGet` | `CoreDate` | None | Filter for clients created after or on a date. |
| `createdLet` | `CoreDate` | None | Filter for clients created before or on a date. |
| `postCode` | `[String!]` | None | Filter for clients with any contact in these post codes. Accepts a single string or an array of strings. |
| `municipality` | `[String!]` | None | Filter for clients with any contact in these municipalities/cities. |
| `region` | `[String!]` | None | Filter for clients with any contact in these regions/states/provinces. |
| `contactsWithEmail` | `ContactsWithEmail` | None | Filter for clients where ALL contacts either have or do not have an email address. |
| `contactsWithPhone` | `ContactsWithPhone` | None | Filter for clients where ALL contacts either have or do not have a phone number. |
| `contactsWithTextablePhone` | `ContactsWithTextablePhone` | None | Filter for clients where ALL contacts either have or do not have a textable phone number. |
| `nextTuningDueGet` | `CoreDate` | None | Filter for clients that have an active piano with the next tuning due after or on a date. |
| `nextTuningDueLet` | `CoreDate` | None | Filter for clients that have an active piano with the next tuning due before or on a date. |
| `anyPianoStatus` | `[PianoStatus!]` | None | Filter for clients that have at least one piano with these statuses. |
| `allPianoStatus` | `[PianoStatus!]` | None | Filter for clients where all of their pianos have these statuses. |
| `allActivePianosLastTunedGet` | `CoreDate` | None | Filter for clients where all of their active pianos were last tuned after or on a date. |
| `allActivePianosLastTunedLet` | `CoreDate` | None | Filter for clients where all of their active pianos were last tuned before or on a date. |
| `allActivePianosNextTuningDueGet` | `CoreDate` | None | Filter for clients where all of their active pianos have the next tuning due after or on a date. |
| `allActivePianosNextTuningDueLet` | `CoreDate` | None | Filter for clients where all of their active pianos have the next tuning due before or on a date. |
| `activePianoCountGet` | `Int` | None | Filter for clients with at least this many active pianos. |
| `activePianoCountLet` | `Int` | None | Filter for clients with at most this many active pianos. |
| `anyTags` | `[String!]` | None | Filter for clients with any of these tags. |
| `allTags` | `[String!]` | None | Filter for clients with all of these tags. |
| `excludeTags` | `[String!]` | None | Filter for clients with none of these tags. |
| `referredBy` | `[String!]` | None | Filter for clients with any of these referred by values. |
| `primaryContactWantsEmail` | `Boolean` | None | Filter for clients where the primary contact wants/does not want email. |
| `primaryContactWantsText` | `Boolean` | None | Filter for clients where the primary contact wants/does not want text. |
| `primaryContactWantsPhone` | `Boolean` | None | Filter for clients where the primary contact wants/does not want phone calls. |

---

### PrivateAllErrorLogsFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `createdGet` | `CoreDate` | None | - |
| `createdLet` | `CoreDate` | None | - |

---

### PrivateAllEstimatesFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `clientId` | `String` | None | - |
| `pianoId` | `String` | None | - |
| `search` | `String` | None | - |
| `createdGet` | `CoreDate` | None | Greater than or equal to. |
| `createdLet` | `CoreDate` | None | Less than or equal to. |
| `expiresGet` | `CoreDate` | None | Greater than or equal to. |
| `expiresLet` | `CoreDate` | None | Less than or equal to. |
| `archived` | `Boolean` | None | - |
| `expired` | `Boolean` | None | - |
| `primaryTierTotalGet` | `Int` | None | Greater than or equal to. |
| `primaryTierTotalLet` | `Int` | None | Less than or equal to. |
| `anyTierTotalGet` | `Int` | None | Greater than or equal to. |
| `anyTierTotalLet` | `Int` | None | Less than or equal to. |
| `recommendedTierTotalGet` | `Int` | None | Greater than or equal to. |
| `recommendedTierTotalLet` | `Int` | None | Less than or equal to. |
| `createdById` | `[String!]` | None | - |
| `assignedToId` | `[String!]` | None | - |
| `pianoType` | `[PianoType!]` | None | - |
| `anyTags` | `[String!]` | None | Filter for estimates with any of these tags. |
| `allTags` | `[String!]` | None | Filter for estimates with all of these tags. |
| `excludeTags` | `[String!]` | None | Filter for estimates with none of these tags. |
| `region` | `[String!]` | None | Filter for estimates with primary contact addresses in any of these regions/states. Uses primary contact street address region. Accepts a single string or an array of strings. |
| `municipality` | `[String!]` | None | Filter for estimates with primary contact addresses in any of these municipalities/cities. Uses primary contact street address municipality. Accepts a single string or an array of strings. |
| `postCode` | `[String!]` | None | Filter for estimates with primary contact addresses in any of these postal codes. Uses primary contact street address postal_code. Accepts a single string or an array of strings. |

---

### PrivateAllEventReservationsFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `status` | `[EventReservationStatus!]` | None | - |
| `search` | `String` | None | - |
| `createdGet` | `CoreDate` | None | Greater than or equal to. |
| `createdLet` | `CoreDate` | None | Less than or equal to. |
| `startsGet` | `CoreDate` | None | Greater than or equal to. |
| `startsLet` | `CoreDate` | None | Less than or equal to. |
| `userId` | `[String!]` | None | The user(s) for which the reservation is scheduled. |
| `requestClientId` | `[String!]` | None | If the client followed a custom link to the scheduler that included their client id in the URL and prefilled all the forms for them, this will be that id. |
| `reviewedClientId` | `[String!]` | None | The client id for the reservation once it has been approved or declined and optionally mapped to a client.  Note that in Gazelle reservations can be declined without mapping to a client. |
| `reservationDateGet` | `CoreDate` | None | Greater than or equal to reservation date. |
| `reservationDateLet` | `CoreDate` | None | Less than or equal to reservation date. |

---

### PrivateAllEventsFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `startOn` | `CoreDate` | None | - |
| `endOn` | `CoreDate` | None | - |
| `clientId` | `[String!]` | None | - |
| `pianoId` | `[String!]` | None | - |
| `userId` | `[String!]` | None | - |
| `search` | `String` | None | - |
| `type` | `[EventType!]` | None | - |
| `status` | `[EventStatus!]` | None | - |
| `dateGet` | `CoreDate` | None | - |
| `dateLet` | `CoreDate` | None | - |
| `appointmentIsTuning` | `Boolean` | None | - |
| `appointmentHasPiano` | `Boolean` | None | - |
| `appointmentIsCompleted` | `Boolean` | None | - |
| `appointmentIsConfirmed` | `Boolean` | None | - |

---

### PrivateAllInvoicesFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `clientId` | `String` | None | - |
| `pianoId` | `String` | None | - |
| `search` | `String` | None | - |
| `status` | `[InvoiceStatus!]` | None | - |
| `archived` | `Boolean` | None | - |
| `invoiceDateGet` | `CoreDate` | None | Greater than or equal to. |
| `invoiceDateLet` | `CoreDate` | None | Less than or equal to. |
| `dueDateGet` | `CoreDate` | None | Greater than or equal to. |
| `dueDateLet` | `CoreDate` | None | Less than or equal to. |
| `paymentDateGet` | `CoreDate` | None | Greater than or equal to. |
| `paymentDateLet` | `CoreDate` | None | Less than or equal to. |
| `totalGet` | `Int` | None | Greater than or equal to. |
| `totalLet` | `Int` | None | Less than or equal to. |
| `tipTotalGet` | `Int` | None | Greater than or equal to. |
| `tipTotalLet` | `Int` | None | Less than or equal to. |
| `tipIncluded` | `Boolean` | None | Filter for invoices with a tip included. |
| `needsQuickbooksSync` | `Boolean` | None | If this is false, it will return all invoices whose last sync was successful and have had no changes since last sync.  If this is true, it returns the invoices that have changed since the last successful sync, the invoices that have never been synced, and invoices whose last sync failed. |
| `invoiceIds` | `[String!]` | None | Filter the list to only these IDs |
| `quickbooksSyncNotices` | `[QuickbooksSyncNoticeType!]` | None | A list of the QuickBooks Online syncing notice types to filter by |
| `createdBy` | `[String!]` | None | A list of user IDs |
| `assignedTo` | `[String!]` | None | A list of user IDs |
| `anyTags` | `[String!]` | None | Filter for invoices with any of these tags. |
| `allTags` | `[String!]` | None | Filter for invoices with all of these tags. |
| `excludeTags` | `[String!]` | None | Filter for invoices with none of these tags. |
| `paymentMethods` | `PaymentMethodFilterInput` | None | Filter for invoices with the given payment method |
| `region` | `[String!]` | None | Filter for invoices with billing addresses in any of these regions/states. Checks alt billing region first, then falls back to contact address region. Accepts a single string or an array of strings. |
| `municipality` | `[String!]` | None | Filter for invoices with billing addresses in any of these municipalities/cities. Checks alt billing municipality first, then falls back to contact address municipality. Accepts a single string or an array of strings. |
| `postCode` | `[String!]` | None | Filter for invoices with billing addresses in any of these postal codes. Checks alt billing post_code first, then falls back to contact address post_code. Accepts a single string or an array of strings. |

---

### PrivateAllPianosFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `clientId` | `String` | None | - |
| `excludePianoIds` | `[String!]` | None | - |
| `search` | `String` | None | - |
| `type` | `[PianoType!]` | None | - |
| `status` | `[PianoStatus!]` | None | - |
| `consignment` | `Boolean` | None | - |
| `rental` | `Boolean` | None | - |
| `rentalContractEndsGet` | `CoreDate` | None | Ending date of the rental contract for the piano. |
| `rentalContractEndsLet` | `CoreDate` | None | Ending date of the rental contract for the piano. |
| `lastTunedGet` | `CoreDate` | None | Last tuned after or on a date. |
| `lastTunedLet` | `CoreDate` | None | Last tuned before or on a date. |
| `nextTuningDueGet` | `CoreDate` | None | Next tuning due after or on a date. |
| `nextTuningDueLet` | `CoreDate` | None | Next tuning due before or on a date. |
| `nextTuningScheduledGet` | `CoreDate` | None | Next tuning scheduled after or on a date. |
| `nextTuningScheduledLet` | `CoreDate` | None | Next tuning scheduled before or on a date. |
| `hasPastTuningScheduled` | `Boolean` | None | Filter pianos that do or do not have a past tuning appointment scheduled. |
| `hasPastAppointmentScheduled` | `Boolean` | None | Filter pianos that do or do not have any kind of past appointment scheduled. |
| `hasFutureTuningScheduled` | `Boolean` | None | Filter pianos that do or do not have a future tuning appointment scheduled. |
| `hasFutureAppointmentScheduled` | `Boolean` | None | Filter pianos that do or do not have any kind of future appointment scheduled. |
| `hasBeenTuned` | `Boolean` | None | Filter pianos that have or have not ever been tuned. |
| `hasServiceInterval` | `Boolean` | None | Filter pianos that have or do not have a service interval. |
| `hasNoLastTuningDateOrInterval` | `Boolean` | None | Filter pianos that are missing either last tuning date or service interval (true) or have both fields populated (false). |
| `lifecycleIds` | `[NullableFilterStringInput!]` | None | Filter pianos by the reminder that the client is assigned to.  To filter for pianos where the client is not assigned to a reminder send a NullableFilterStringInput value of null. |
| `make` | `[String!]` | None | Filter pianos where the make contains this value. Accepts a single string or an array of strings. This is case insensitive. |
| `serialNumber` | `[String!]` | None | Filter pianos where the serial number contains this value. Accepts a single string or an array of strings. This is case insensitive. |
| `hasTimelineActivityGet` | `CoreDate` | None | Filter for pianos with timeline activity after or on a date. |
| `hasTimelineActivityLet` | `CoreDate` | None | Filter for pianos with timeline activity before or on a date. |
| `hasNoTimelineActivityGet` | `CoreDate` | None | Filter for pianos with NO timeline activity after or on a date. |
| `hasNoTimelineActivityLet` | `CoreDate` | None | Filter for pianos with NO timeline activity before or on a date. |
| `serviceIntervalMonthsGet` | `Int` | None | Filter for pianos with a service interval greater than or equal to a value. |
| `serviceIntervalMonthsLet` | `Int` | None | Filter for pianos with a service interval less than or equal to a value. |
| `yearGet` | `Int` | None | Filter for pianos with a year manufactured greater than or equal to a value. |
| `yearLet` | `Int` | None | Filter for pianos with a year manufactured less than or equal to a value. |
| `needsRepairOrRebuilding` | `Boolean` | None | Filter for pianos that need repair or rebuilding. |
| `isTotalLoss` | `Boolean` | None | Filter for pianos that are marked as a total loss. |
| `useType` | `String` | None | Filter pianos where the use type contains this value.  This is case insensitive. |
| `createdGet` | `CoreDate` | None | Filter for pianos created after or on a date. |
| `createdLet` | `CoreDate` | None | Filter for pianos created before or on a date. |
| `hasManuallyEnteredServiceHistory` | `Boolean` | None | Filter for pianos with at least 1 manually entered service history note. |
| `hasInvoiceGet` | `CoreDate` | None | Filter for pianos with an "invoice date" after or on a date. |
| `hasInvoiceLet` | `CoreDate` | None | Filter for pianos with an "invoice date" before or on a date. |
| `hasAppointmentGet` | `CoreDate` | None | Filter for pianos with a non canceled appointment after or on a date. |
| `hasAppointmentLet` | `CoreDate` | None | Filter for pianos with a non canceled appointment before or on a date. |
| `hasPlayerInstalled` | `Boolean` | None | Filter for pianos that have a player system installed. |
| `playerModel` | `[String!]` | None | Filter pianos where the player model contains this value. Accepts a single string or an array of strings. This is case insensitive. |
| `hasPianoLifeSaverInstalled` | `Boolean` | None | Filter for pianos that have a piano life saver system installed. |
| `hasIvory` | `Boolean` | None | Filter for pianos that have ivory. |
| `caseColor` | `String` | None | Filter for piano case color. |
| `caseFinish` | `String` | None | Filter for piano case finish. |
| `size` | `String` | None | Filter for piano size. |
| `mostRecentPastAppointmentWasTuning` | `Boolean` | None | Filter for pianos where the most recent past appointment was a tuning. |
| `anyTags` | `[String!]` | None | Filter for pianos with any of these tags. |
| `allTags` | `[String!]` | None | Filter for pianos with all of these tags. |
| `excludeTags` | `[String!]` | None | Filter for pianos with none of these tags. |

---

### PrivateAllSentOrScheduledMessagesFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `search` | `String` | None | - |
| `types` | `[SentOrScheduledMessageType!]` | None | - |
| `deliveryTypes` | `[SentOrScheduledMessageDeliveryType!]` | None | - |
| `sources` | `[SentOrScheduledMessageSource!]` | None | - |
| `statuses` | `[SentOrScheduledMessageStatus!]` | None | - |

---

### PrivateAllUncompletedAppointmentsFilter

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `userId` | `[String!]` | None | - |
| `search` | `String` | None | - |
| `startGet` | `CoreDate` | None | Greater than or equal to. |
| `startLet` | `CoreDate` | None | Less than or equal to. |
| `dateGet` | `CoreDate` | None | - |
| `dateLet` | `CoreDate` | None | - |

---

### PrivateApproveEventReservationAddressInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `addressId` | `String` | None | - |
| `replaceExistingType` | `Boolean` | None | - |
| `type` | `ContactAddressType` | None | - |
| `address1` | `String` | None | - |
| `address2` | `String` | None | - |
| `city` | `String` | None | - |
| `state` | `String` | None | - |
| `zip` | `String` | None | - |

---

### PrivateApproveEventReservationClientInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `clientId` | `String` | None | - |
| `status` | `ClientStatus` | None | - |

---

### PrivateApproveEventReservationContactInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `contactId` | `String` | None | - |
| `firstName` | `String` | None | - |
| `lastName` | `String` | None | - |
| `isDefault` | `Boolean` | None | - |

---

### PrivateApproveEventReservationEmailInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `emailId` | `String` | None | - |
| `isDefault` | `Boolean` | None | - |
| `email` | `String` | None | - |

---

### PrivateApproveEventReservationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `client` | `PrivateApproveEventReservationClientInput!` | None | - |
| `contact` | `PrivateApproveEventReservationContactInput!` | None | - |
| `email` | `PrivateApproveEventReservationEmailInput` | None | - |
| `phone` | `PrivateApproveEventReservationPhoneInput` | None | - |
| `location` | `PrivateApproveEventReservationLocationInput` | None | - |
| `start` | `CoreDateTime` | None | An option override start time of the event.  If not provided, we will use the start time from the reservation. |
| `timezone` | `String` | None | An option override timezone of the event.  If not provided, we will use the timezone from the reservation. |
| `duration` | `Int` | None | An option override duration of the event.  If not provided, we will use the duration from the reservation. |
| `buffer` | `Int` | None | An option override buffer of the event.  If not provided, we will use the buffer from the reservation. |
| `userId` | `String` | None | An option override user id of the event.  If not provided, we will use the user id from the reservation. |
| `pianos` | `[PrivateApproveEventReservationPianoInput!]!` | None | - |
| `eventNotes` | `String!` | None | - |
| `eventTitle` | `String!` | None | - |
| `wantsEmail` | `Boolean` | None | Indicates whether to send a notification of approval email to the client or not |
| `emailSubject` | `String` | None | - |
| `emailMessage` | `String` | None | - |
| `deleteEventIds` | `[String!]` | None | - |

---

### PrivateApproveEventReservationLocationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `locationId` | `String` | None | - |
| `replaceExistingType` | `Boolean` | None | - |
| `locationType` | `ContactLocationType` | None | - |
| `usageType` | `ContactLocationUsageType` | None | - |
| `street1` | `String` | None | - |
| `street2` | `String` | None | - |
| `municipality` | `String` | None | - |
| `region` | `String` | None | - |
| `postalCode` | `String` | None | - |
| `countryCode` | `String` | None | - |
| `latitude` | `String` | None | - |
| `longitude` | `String` | None | - |
| `what3words` | `String` | None | - |

---

### PrivateApproveEventReservationPhoneInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `phoneId` | `String` | None | - |
| `type` | `PhoneType` | None | - |
| `isDefault` | `Boolean` | None | - |
| `phoneNumber` | `String` | None | - |

---

### PrivateApproveEventReservationPianoInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `isTuning` | `Boolean` | None | - |
| `pianoId` | `String` | None | - |
| `make` | `String!` | None | - |
| `type` | `PianoType!` | None | - |
| `model` | `String` | None | - |
| `location` | `String` | None | - |

---

### PrivateBulkPauseClientsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `action` | `BulkPauseClientsAction!` | None | Action to perform on clients |
| `noContactUntil` | `ISO8601Date` | None | Date until which to pause reminders (required when action is 'pause') |

---

### PrivateCancelBillingPlanInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `reasons` | `[String!]` | None | - |

---

### PrivateChangeClientStatusInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `status` | `ClientStatus!` | None | - |
| `removeFutureAppointments` | `Boolean` | None | - |
| `reasonInactiveCode` | `String` | None | - |
| `reasonInactiveDetails` | `String` | None | - |
| `createMailchimpTag` | `Boolean` | None | If set and if the Mailchimp integration is configured, the clients that have changed their status will be added to a Mailchimp tag. |
| `includeClientsThatDontWantEmailsInMailchimpExport` | `Boolean` | None | If set and if the Mailchimp integration is configured, clients do not want emails will be added to a Mailchimp tag. |
| `timelineComment` | `String` | None | Optional timeline comment to add to all affected clients |

---

### PrivateChangePianoStatusInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `status` | `PianoStatus!` | None | - |
| `createMailchimpTag` | `Boolean` | None | If set and if the Mailchimp integration is configured, the clients for pianos that have changed their status will be added to a Mailchimp tag. |
| `includeClientsThatDontWantEmailsInMailchimpExport` | `Boolean` | None | If set and if the Mailchimp integration is configured, clients do not want emails will be added to a Mailchimp tag. |
| `timelineComment` | `String` | None | Optional timeline comment to add to all affected pianos |

---

### PrivateClientInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `referenceId` | `String` | None | - |
| `companyName` | `String` | None | - |
| `region` | `String` | None | - |
| `preferredTechnicianId` | `String` | None | - |
| `status` | `ClientStatus` | None | - |
| `lastResultNotes` | `String` | None | - |
| `preferenceNotes` | `String` | None | - |
| `noContactUntil` | `CoreDate` | None | - |
| `referredBy` | `String` | None | - |
| `referredByNotes` | `String` | None | - |
| `reasonInactiveDetails` | `String` | None | - |
| `custom1` | `String` | None | - |
| `custom2` | `String` | None | - |
| `custom3` | `String` | None | - |
| `custom4` | `String` | None | - |
| `custom5` | `String` | None | - |
| `custom6` | `String` | None | - |
| `custom7` | `String` | None | - |
| `custom8` | `String` | None | - |
| `custom9` | `String` | None | - |
| `custom10` | `String` | None | - |
| `reasonInactiveCode` | `String` | None | - |
| `noContactReason` | `String` | None | - |
| `lifecycleId` | `String` | None | - |
| `personalNotes` | `String` | None | - |
| `ignoreSafetyChecks` | `Boolean` | None | - |
| `referralClientId` | `String` | None | - |
| `clientType` | `String` | None | - |
| `contacts` | `[PrivateContactInput!]` | None | - |
| `removeFutureAppointments` | `Boolean` | None | When changing status to inactive, you can set this to true and all future appointments will be removed from the calendar. |
| `tags` | `[String!]` | None | A list of tags to apply to this client.  If a tag does not exist, it will be created. |
| `localizationId` | `String` | None | Sets a specific localization to use when displaying things to this client.  If this is not set, then the preferred technician's defaultClientLocalization will be used.  If that is not set, then the company's global default client localization will be used. Look at allLocalizations to get a list of all possible localizations to use. |

---

### PrivateClientLogInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `comment` | `String` | None | - |
| `createdAt` | `CoreDateTime` | None | - |

---

### PrivateCompanyBillingSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `stripeCustomerTaxIds` | `[PrivateCompanyBillingSettingsStripeCustomerTaxIdInput!]` | None | A list of the Tax IDs to set on the Stripe Customer record.  These Tax IDs can be displayed on Gazelle subscription invoices. |
| `showTaxIdsOnInvoices` | `Boolean` | None | Whether or not to show the Tax IDs on Gazelle subscription invoices. |
| `stripeCustomerAddress` | `PrivateCompanyBillingSettingsStripeAddressInput` | None | The address that is set on the Stripe's Customer record.  This address is displayed on Gazelle subscription invoices. |
| `showAddressOnInvoices` | `Boolean` | None | Whether or not to show the address on Gazelle subscription invoices. |
| `stripeCustomerPhoneNumber` | `String` | None | The phone number that is set on the Stripe's Customer record.  This phone number is displayed on Gazelle subscription invoices. |
| `showPhoneNumberOnInvoices` | `Boolean` | None | Whether or not to show the phone number on Gazelle subscription invoices. |
| `receiptEmail` | `String` | None | - |

---

### PrivateCompanyBillingSettingsStripeAddressInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `line1` | `String` | None | - |
| `line2` | `String` | None | - |
| `municipality` | `String` | None | - |
| `region` | `String` | None | - |
| `postalCode` | `String` | None | - |
| `countryCode` | `String` | None | - |

---

### PrivateCompanyBillingSettingsStripeCustomerTaxIdInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `type` | `String` | None | - |
| `value` | `String` | None | - |

---

### PrivateCompanyBrandingSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `maxLogoPx` | `Int` | None | The maximum width or height of the logo in pixels. |
| `headerLayout` | `HeaderLayout` | None | The layout of the header. |
| `primaryColor` | `String` | None | The primary color for the company's branding. |
| `showCompanyPhone` | `Boolean` | None | Whether or not to show the company's phone number on public-facing client interfaces. |
| `showCompanyEmail` | `Boolean` | None | Whether or not to show the company's email address on public-facing client interfaces. |
| `showCompanyAddress` | `Boolean` | None | Whether or not to show the company's address on public-facing client interfaces. |
| `privacyPolicy` | `I18nString` | None | The company's privacy policy displayed to clients on public-facing interfaces (like the self-scheduler, invoices, estimates, etc). |
| `termsOfService` | `I18nString` | None | The company's terms of service displayed to clients on public-facing interfaces (like the self-scheduler, invoices, estimates, etc). |

---

### PrivateCompanyClientSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `defaultWantsText` | `Boolean` | None | - |

---

### PrivateCompanyEstimateSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `nextEstimateNumber` | `Int` | None | - |
| `defaultMonthsExpiresOn` | `Int` | None | - |
| `defaultNotes` | `I18nString` | None | - |
| `sendQuestionsToAllActiveAdmins` | `Boolean` | None | - |
| `sendQuestionsToCreator` | `Boolean` | None | - |
| `sendQuestionsToEmails` | `[String!]` | None | - |

---

### PrivateCompanyFeatureTogglesInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `publicV2Enabled` | `Boolean` | None | - |

---

### PrivateCompanyGeneralSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `receiptEmail` | `String` | None | - |
| `emailSender` | `String` | None | - |
| `hourlyRate` | `BigInt` | None | - |
| `capitalizeNames` | `Boolean` | None | - |
| `clientCustom1Label` | `String` | None | - |
| `clientCustom2Label` | `String` | None | - |
| `clientCustom3Label` | `String` | None | - |
| `clientCustom4Label` | `String` | None | - |
| `clientCustom5Label` | `String` | None | - |
| `clientCustom6Label` | `String` | None | - |
| `clientCustom7Label` | `String` | None | - |
| `clientCustom8Label` | `String` | None | - |
| `clientCustom9Label` | `String` | None | - |
| `clientCustom10Label` | `String` | None | - |
| `distanceUnit` | `SchedulerDistanceUnitType` | None | - |

---

### PrivateCompanyInvoicesSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `defaultInvoiceNetDays` | `Int` | None | - |
| `nextInvoiceNumber` | `Int` | None | - |
| `defaultInvoicePaymentType` | `InvoicePaymentType` | None | - |
| `defaultUserPaymentOption` | `UserPaymentOption` | None | - |
| `defaultInvoiceNotes` | `String` | None | - |
| `defaultInvoiceTopNotes` | `String` | None | - |
| `defaultInvoiceNotesHeader` | `String` | None | - |
| `defaultInvoiceTopNotesHeader` | `String` | None | - |
| `tipsEnabled` | `Boolean` | None | - |
| `tipsPublicGuiAutoselect` | `Boolean` | None | - |
| `showTopNotes` | `Boolean` | None | - |
| `calculatePianoInvoiceLastService` | `Boolean` | None | Whether or not to use the invoice date on open/paid invoices to calculate the last service date for pianos. |

---

### PrivateCompanyLocalizationSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `defaultCurrencyCode` | `String` | None | This is the currency code to be used for all currency formatting for this (e.g. USD, CAD, etc).  It must be one of the supported currency codes. |
| `defaultUserLocalizationId` | `String` | None | This sets the default user localization for this company.  It must be one of the localizations defined in allLocalizations |
| `defaultClientLocalizationId` | `String` | None | This sets the default client localization for the company.  This is the localization that will be used for displaying things to clients if no other client localization overrides have been set for a client. |

---

### PrivateCompanyPermissionsSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `assistantsViewCompanyMetrics` | `Boolean` | None | - |
| `limitedAdminsViewCompanyMetrics` | `Boolean` | None | - |
| `techniciansViewCompanyMetrics` | `Boolean` | None | - |

---

### PrivateCompanyPianosSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `defaultServiceIntervalMonths` | `Int` | None | - |

---

### PrivateCompanyProfileSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `String` | None | - |
| `phoneNumber` | `String` | None | - |
| `email` | `String` | None | - |
| `website` | `String` | None | - |
| `street1` | `String` | None | - |
| `street2` | `String` | None | - |
| `municipality` | `String` | None | - |
| `region` | `String` | None | - |
| `postalCode` | `String` | None | - |
| `countryCode` | `String` | None | - |

---

### PrivateCompanyQuickbooksOnlineSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `syncGazelleUsersAsQboClasses` | `Boolean` | None | - |
| `syncStripePayouts` | `Boolean` | None | - |
| `pullPayments` | `Boolean` | None | - |
| `syncStartDate` | `CoreDate` | None | - |
| `allowOnlineCreditCardPayment` | `Boolean` | None | - |
| `allowOnlineAchPayment` | `Boolean` | None | - |

---

### PrivateCompanySelfSchedulerSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `welcomeMessage` | `I18nString` | None | - |
| `reservationCompleteMessage` | `I18nString` | None | - |
| `noAvailabilityMessage` | `I18nString` | None | - |
| `outsideServiceAreaMessage` | `I18nString` | None | - |
| `showCosts` | `Boolean` | None | - |
| `reservationCompleteBehavior` | `ReservationCompleteBehavior` | None | - |
| `technicianSelectionBehavior` | `TechnicianSelectionBehavior` | None | - |
| `selfSchedulerEnabled` | `Boolean` | None | - |
| `includeIcsAttachmentOnNewAppointmentEmails` | `Boolean` | None | - |
| `allowCoordinateLocationType` | `Boolean` | None | - |
| `allowWhat3wordsLocationType` | `Boolean` | None | - |

---

### PrivateCompanySettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `profile` | `PrivateCompanyProfileSettingsInput` | None | - |
| `general` | `PrivateCompanyGeneralSettingsInput` | None | - |
| `client` | `PrivateCompanyClientSettingsInput` | None | - |
| `localization` | `PrivateCompanyLocalizationSettingsInput` | None | - |
| `permissions` | `PrivateCompanyPermissionsSettingsInput` | None | - |
| `estimates` | `PrivateCompanyEstimateSettingsInput` | None | - |
| `stripePayments` | `PrivateCompanyStripePaymentsSettingsInput` | None | - |
| `quickbooksOnline` | `PrivateCompanyQuickbooksOnlineSettingsInput` | None | - |
| `invoices` | `PrivateCompanyInvoicesSettingsInput` | None | - |
| `pianos` | `PrivateCompanyPianosSettingsInput` | None | - |
| `branding` | `PrivateCompanyBrandingSettingsInput` | None | - |
| `selfScheduler` | `PrivateCompanySelfSchedulerSettingsInput` | None | - |
| `legacySelfScheduler` | `PrivateLegacyCompanySelfSchedulerSettingsInput` | None | - |
| `billing` | `PrivateCompanyBillingSettingsInput` | None | - |
| `locationBias` | `PrivateLocationBiasInput` | None | - |
| `smsSettings` | `PrivateCompanySmsSettingsInput` | None | - |

---

### PrivateCompanySmsSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `isEnabled` | `Boolean` | None | - |
| `requireClientOptIn` | `Boolean` | None | - |
| `defaultReplyMessage` | `String` | None | - |
| `deliveryWindows` | `[PrivateDeliveryWindowInput!]` | None | - |

---

### PrivateCompanyStripePaymentsSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `acceptedPaymentMethods` | `[StripePaymentMethods!]` | None | - |
| `defaultAcceptElectronicPayments` | `Boolean` | None | Whether or not new invoices should accept electronic payment by default or not. |

---

### PrivateCompleteEventInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `resultType` | `CompletionResultType!` | None | - |
| `errorReferenceId` | `String` | None | - |
| `clientTimelineComment` | `String` | None | - |
| `clientPersonalNotes` | `String` | None | - |
| `clientPreferenceNotes` | `String` | None | - |
| `serviceHistoryNotes` | `[PrivateCompletionServiceHistoryInput!]` | None | - |
| `resetNextServiceOverrides` | `[PrivateCompletionResetNextServiceOverrideInput!]` | None | - |
| `scheduledMessages` | `[PrivateCompletionScheduledMessageInput!]` | None | - |
| `pianoMeasurements` | `[PrivatePianoMeasurementInput!]` | None | - |
| `invoice` | `PrivateCreateInvoiceInput` | None | - |

---

### PrivateCompletionResetNextServiceOverrideInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `pianoId` | `String!` | None | - |
| `nextServiceOverride` | `CoreDate` | None | - |

---

### PrivateCompletionScheduledMessageInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `type` | `ScheduledMessageType` | None | - |
| `errorReferenceId` | `String` | None | - |
| `scheduledMessageTemplateId` | `String` | None | - |
| `language` | `String` | None | - |
| `subject` | `String` | None | - |
| `template` | `String` | None | - |
| `sendAt` | `CoreDateTime` | None | - |

---

### PrivateCompletionServiceHistoryInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `pianoId` | `String!` | None | - |
| `notes` | `String!` | None | - |

---

### PrivateConfirmEventInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `isSilent` | `Boolean` | None | - |

---

### PrivateContactAddressInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `ContactAddressType` | None | - |
| `address1` | `String` | None | - |
| `address2` | `String` | None | - |
| `city` | `String` | None | - |
| `state` | `String` | None | - |
| `zip` | `String` | None | - |
| `geoZone` | `String` | None | - |

---

### PrivateContactEmailInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `isDefault` | `Boolean` | None | - |
| `email` | `String` | None | - |

---

### PrivateContactInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `role` | `String` | None | - |
| `isDefault` | `Boolean` | None | - |
| `isBillingDefault` | `Boolean` | None | - |
| `firstName` | `String` | None | - |
| `middleName` | `String` | None | - |
| `lastName` | `String` | None | - |
| `title` | `String` | None | - |
| `suffix` | `String` | None | - |
| `wantsEmail` | `Boolean` | None | - |
| `wantsText` | `Boolean` | None | - |
| `wantsPhone` | `Boolean` | None | - |
| `archived` | `Boolean` | None | - |
| `emails` | `[PrivateContactEmailInput!]` | None | - |
| `phones` | `[PrivateContactPhoneInput!]` | None | - |
| `locations` | `[PrivateContactLocationInput!]` | None | - |

---

### PrivateContactInputWithoutNestedCollections

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `role` | `String` | None | - |
| `isDefault` | `Boolean` | None | - |
| `isBillingDefault` | `Boolean` | None | - |
| `firstName` | `String` | None | - |
| `middleName` | `String` | None | - |
| `lastName` | `String` | None | - |
| `title` | `String` | None | - |
| `suffix` | `String` | None | - |
| `wantsEmail` | `Boolean` | None | - |
| `wantsText` | `Boolean` | None | - |
| `wantsPhone` | `Boolean` | None | - |
| `archived` | `Boolean` | None | - |

---

### PrivateContactLocationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `locationType` | `ContactLocationType` | None | - |
| `usageType` | `ContactLocationUsageType` | None | - |
| `street1` | `String` | None | When the locationType is ADDRESS, this is the first line of the address.  This argument is ignored when the locationType is not ADDRESS. |
| `street2` | `String` | None | When the locationType is ADDRESS, this is the second line of the address.  This argument is ignored when the locationType is not ADDRESS. |
| `municipality` | `String` | None | When the locationType is ADDRESS, this is the city.  This argument is ignored when the locationType is not ADDRESS. |
| `region` | `String` | None | When the locationType is ADDRESS, this is the state or province.  This argument is ignored when the locationType is not ADDRESS. |
| `postalCode` | `String` | None | When the locationType is ADDRESS, this is the postal code.  This argument is ignored when the locationType is not ADDRESS. |
| `countryCode` | `String` | None | When the locationType is ADDRESS, this is the country code.  This argument is ignored when the locationType is not ADDRESS.   |
| `latitude` | `String` | None | When the locationType is COORDINATES, this is the latitude of the coordinates.  This argument is ignored when the locationType is not COORDINATES. |
| `longitude` | `String` | None | When the locationType is COORDINATES, this is the longitude of the coordinates.  This argument is ignored when the locationType is not COORDINATES. |
| `what3words` | `String` | None | When the locationType is WHAT3WORDS, this is the what3words address.  This argument is ignored when the locationType is not WHAT3WORDS. |

---

### PrivateContactPhoneInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `PhoneType` | None | - |
| `isDefault` | `Boolean` | None | - |
| `phoneNumber` | `String` | None | - |
| `extension` | `String` | None | - |

---

### PrivateCoordinatesInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `latitude` | `String!` | None | - |
| `longitude` | `String!` | None | - |

---

### PrivateCreateBulkAddClientTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkAddEstimateTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkAddInvoiceTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkAddPianoTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkArchiveEstimateJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `isArchived` | `Boolean!` | None | - |

---

### PrivateCreateBulkArchiveInvoiceJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `isArchived` | `Boolean!` | None | - |

---

### PrivateCreateBulkExportClientsToMailchimpInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `includeClientsThatDontWantEmails` | `Boolean` | None | - |

---

### PrivateCreateBulkMarkAppointmentsCompleteJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `status` | `CompletionResultType!` | None | - |

---

### PrivateCreateBulkReminderReassignmentInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `lifecycleId` | `String` | None | - |

---

### PrivateCreateBulkRemoveClientTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkRemoveEstimateTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkRemoveInvoiceTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateBulkRemovePianoTagJobInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `String` | None | - |

---

### PrivateCreateEstimateInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `clientId` | `String!` | None | - |
| `contactId` | `String` | None | - |
| `assignedToId` | `String` | None | - |
| `pianoId` | `String!` | None | - |
| `pianoPhotoId` | `String` | None | - |
| `locale` | `String` | None | - |
| `notes` | `String` | None | - |
| `expiresOn` | `CoreDate!` | None | - |
| `estimatedOn` | `CoreDate!` | None | - |
| `currentPerformanceLevel` | `Float` | None | - |
| `isArchived` | `Boolean` | None | - |
| `tags` | `[String!]` | None | - |
| `pianoPotentialPerformanceLevel` | `Float` | None | - |
| `estimateTiers` | `[PrivateEstimateTierInput!]` | None | - |

---

### PrivateCreateInvoiceInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `clientId` | `String` | None | - |
| `contactId` | `String` | None | - |
| `assignedToId` | `String` | None | - |
| `dueOn` | `CoreDate` | None | - |
| `status` | `InvoiceStatus` | None | - |
| `notesHeader` | `String` | None | - |
| `notes` | `String` | None | - |
| `topNotesHeader` | `String` | None | - |
| `topNotes` | `String` | None | - |
| `netDays` | `Int` | None | - |
| `altBillingFirstName` | `String` | None | - |
| `altBillingLastName` | `String` | None | - |
| `altBillingCompanyName` | `String` | None | - |
| `altBillingStreet1` | `String` | None | - |
| `altBillingStreet2` | `String` | None | - |
| `altBillingMunicipality` | `String` | None | - |
| `altBillingRegion` | `String` | None | - |
| `altBillingPostalCode` | `String` | None | - |
| `altBillingCountryCode` | `String` | None | - |
| `altBillingEmail` | `String` | None | - |
| `altBillingPhone` | `String` | None | - |
| `summarize` | `Boolean` | None | - |
| `archived` | `Boolean` | None | - |
| `currencyCode` | `String` | None | - |
| `acceptElectronicPayment` | `Boolean` | None | - |
| `acceptedElectronicPaymentMethods` | `[StripePaymentMethods!]` | None | - |
| `paymentAmount` | `Int` | None | - |
| `paymentType` | `InvoicePaymentType` | None | - |
| `paymentNotes` | `String` | None | - |
| `paymentPaidAt` | `CoreDateTime` | None | - |
| `paymentTipAmount` | `Int` | None | - |
| `invoiceItems` | `[PrivateInvoiceItemInput!]` | None | - |
| `emailToAltBilling` | `Boolean` | None | - |
| `emailToContactEmailIds` | `[String!]` | None | - |
| `attachPdf` | `Boolean` | None | - |
| `emailSubject` | `String` | None | Custom email subject to use instead of the default |
| `emailMessage` | `String` | None | Custom email message to use instead of the template |
| `estimateTierId` | `String` | None | - |
| `tags` | `[String!]` | None | - |

---

### PrivateCreateUserInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `firstName` | `String!` | None | - |
| `lastName` | `String!` | None | - |
| `email` | `String!` | None | - |
| `accessLevel` | `AccessLevel!` | None | - |

---

### PrivateDeclineEventReservationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `clientId` | `String` | None | - |
| `deleteEventIds` | `[String!]` | None | - |
| `wantsEmail` | `Boolean` | None | Indicates whether to send an email declining the reservation to the client or not |
| `emailSubject` | `String` | None | - |
| `emailMessage` | `String` | None | - |

---

### PrivateDeleteTagInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `tag` | `ID!` | None | - |
| `modelType` | `PrivateTagModelType!` | None | - |

---

### PrivateDeliveryWindowInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `dayOfWeek` | `Weekdays!` | None | - |
| `startHour` | `Int!` | None | - |
| `endHour` | `Int!` | None | - |

---

### PrivateEstimateChecklistGroupInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `I18nStringInput` | None | - |
| `sequenceNumber` | `Int` | None | - |
| `estimateChecklistItems` | `[PrivateEstimateChecklistItemInput!]` | None | - |

---

### PrivateEstimateChecklistInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `I18nStringInput` | None | - |
| `isDefault` | `Boolean` | None | - |
| `estimateChecklistGroups` | `[PrivateEstimateChecklistGroupInput!]` | None | - |
| `ungroupedEstimateChecklistItems` | `[PrivateEstimateChecklistItemInput!]` | None | - |

---

### PrivateEstimateChecklistItemInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `I18nStringInput` | None | - |
| `masterServiceItemId` | `String` | None | - |
| `sequenceNumber` | `Int` | None | - |

---

### PrivateEstimateTierGroupInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `String` | None | - |
| `sequenceNumber` | `Int` | None | - |
| `estimateTierItems` | `[PrivateEstimateTierItemInput!]` | None | - |

---

### PrivateEstimateTierInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `recommendationId` | `String` | None | - |
| `targetPerformanceLevel` | `Float` | None | - |
| `sequenceNumber` | `Int` | None | - |
| `notes` | `String` | None | - |
| `isPrimary` | `Boolean` | None | - |
| `allowSelfSchedule` | `Boolean` | None | - |
| `estimateTierGroups` | `[PrivateEstimateTierGroupInput!]` | None | - |
| `ungroupedEstimateTierItems` | `[PrivateEstimateTierItemInput!]` | None | - |

---

### PrivateEstimateTierItemInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `masterServiceItemId` | `String` | None | - |
| `name` | `String` | None | - |
| `sequenceNumber` | `Int` | None | - |
| `description` | `String` | None | - |
| `educationDescription` | `String` | None | - |
| `quantity` | `Int` | None | - |
| `amount` | `Int` | None | - |
| `duration` | `Int` | None | - |
| `type` | `MasterServiceItemType` | None | - |
| `externalUrl` | `String` | None | - |
| `isTaxable` | `Boolean` | None | - |
| `isTuning` | `Boolean` | None | - |
| `taxes` | `[PrivateEstimateTierItemTaxInput!]` | None | - |
| `photos` | `[PrivateEstimateTierItemPhotoInput!]` | None | - |

---

### PrivateEstimateTierItemPhotoInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `sequenceNumber` | `Int` | None | - |
| `pianoPhotoId` | `String` | None | - |
| `estimateTierItemId` | `String` | None | - |

---

### PrivateEstimateTierItemTaxInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `taxId` | `String` | None | - |
| `name` | `String` | None | - |
| `rate` | `Int` | None | - |
| `total` | `Int` | None | - |

---

### PrivateEventCancelNoticeInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `status` | `EventCancelNoticeStatus` | None | - |

---

### PrivateEventInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `status` | `EventStatus` | None | This should usually not be set.  It is used for special cases where we need to manually reset the event status. |
| `confirmedAt` | `CoreDateTime` | None | This should usually not be set.  It is used for special cases where we need to manually set the confirmed_at date. |
| `start` | `CoreDateTime` | None | - |
| `timezone` | `String` | None | - |
| `duration` | `Int` | None | - |
| `buffer` | `Int` | None | - |
| `title` | `String` | None | - |
| `notes` | `String` | None | - |
| `type` | `EventType` | None | - |
| `location` | `PrivateEventLocationInput` | None | - |
| `isAllDay` | `Boolean` | None | - |
| `clientId` | `String` | None | - |
| `client` | `PrivateClientInput` | None | If present, this will add a new client.  If not present, then clientId should be set for appointments. |
| `userId` | `String` | None | - |
| `pianos` | `[PrivateEventPianoInput!]` | None | - |
| `recurrenceType` | `EventRecurrenceType` | None | - |
| `recurrenceWeekdays` | `[Int!]` | None | - |
| `recurrenceWeeks` | `[Int!]` | None | - |
| `recurrenceDates` | `[Int!]` | None | - |
| `recurrenceInterval` | `Int` | None | - |
| `recurrenceEndingType` | `EventRecurrenceEndingType` | None | - |
| `recurrenceEndingOccurrences` | `Int` | None | - |
| `recurrenceEndingDate` | `CoreDate` | None | - |
| `isConfirmationEmailWanted` | `Boolean` | None | - |
| `confirmationEmailSubject` | `String` | None | Custom email subject to use instead of the template when sending confirmation email |
| `confirmationEmailMessage` | `String` | None | Custom email message to use instead of the template when sending confirmation email |
| `recurrenceChangeType` | `EventRecurrenceChangeType` | None | - |
| `schedulerV2SearchId` | `String` | None | - |
| `travelMode` | `SchedulerTravelMode` | None | - |
| `availabilityId` | `String` | None | - |

---

### PrivateEventLocationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `locationType` | `EventLocationType` | None | - |
| `street1` | `String` | None | When the locationType is ADDRESS, this is the first line of the address.  This argument is ignored when the locationType is not ADDRESS. |
| `street2` | `String` | None | When the locationType is ADDRESS, this is the second line of the address.  This argument is ignored when the locationType is not ADDRESS. |
| `municipality` | `String` | None | When the locationType is ADDRESS, this is the city.  This argument is ignored when the locationType is not ADDRESS. |
| `region` | `String` | None | When the locationType is ADDRESS, this is the state or province.  This argument is ignored when the locationType is not ADDRESS. |
| `postalCode` | `String` | None | When the locationType is ADDRESS, this is the postal code.  This argument is ignored when the locationType is not ADDRESS. |
| `countryCode` | `String` | None | When the locationType is ADDRESS, this is the country code.  This argument is ignored when the locationType is not ADDRESS.   |
| `latitude` | `String` | None | When the locationType is COORDINATES, this is the latitude of the coordinates.  This argument is ignored when the locationType is not COORDINATES. |
| `longitude` | `String` | None | When the locationType is COORDINATES, this is the longitude of the coordinates.  This argument is ignored when the locationType is not COORDINATES. |
| `what3words` | `String` | None | When the locationType is WHAT3WORDS, this is the what3words address.  This argument is ignored when the locationType is not WHAT3WORDS. |
| `singleLineAddress` | `String` | None | When the locationType is SINGLE_LINE_ADDRESS, this is the single line address for the event location.  It is a combination of the street1, street2, municipality, region, postal_code, and country_code fields.  This argument is ignored when the locationType is not SINGLE_LINE_ADDRESS. |

---

### PrivateEventPianoInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `pianoId` | `String` | None | - |
| `isTuning` | `Boolean` | None | - |
| `piano` | `PrivatePianoInput` | None | - |

---

### PrivateInvoiceItemInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `description` | `String` | None | - |
| `type` | `InvoiceItemType` | None | - |
| `billable` | `Boolean` | None | - |
| `amount` | `Int` | None | - |
| `quantity` | `Int` | None | - |
| `taxable` | `Boolean` | None | - |
| `taxes` | `[PrivateInvoiceItemTaxInput!]` | None | - |
| `pianoId` | `String` | None | - |
| `masterServiceItemId` | `String` | None | - |
| `sequenceNumber` | `Int` | None | - |

---

### PrivateInvoiceItemTaxInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `id` | `String` | None | - |
| `taxId` | `String` | None | - |
| `name` | `String` | None | - |
| `rate` | `Int` | None | - |
| `total` | `Int` | None | - |

---

### PrivateInvoicePaymentInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `amount` | `Int` | None | The total amount of the payment.  This number should include any tip amount. |
| `type` | `InvoicePaymentType` | None | - |
| `notes` | `String` | None | - |
| `tipTotal` | `Int` | None | The amount (if any) of paymentAmount that is a tip. |
| `paidAt` | `CoreDateTime` | None | The date and time of the payment in UTC. |

---

### PrivateLegacyCompanySelfSchedulerSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `outsideServiceAreaMessage` | `String` | None | - |
| `selfScheduleSpecialInstructions` | `String` | None | - |
| `selfScheduleCompletionMessage` | `String` | None | - |
| `selfScheduleCompletionRedirect` | `String` | None | - |

---

### PrivateLocalizationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `isUserDefault` | `Boolean` | None | If true, this will become the company-wide default localization for users who have not set their own localization preference. |
| `isClientDefault` | `Boolean` | None | If true, this will become the company-wide default localization for clients who do not have a specific localization set, and whose preferred technician does not have a client localization set. |
| `locale` | `String` | None | The locale (e.g. 'en_US' or 'fr_CA') to use for translations. |
| `dateFormatLocale` | `String` | None | The locale (e.g. 'en_US' or 'fr_CA') to use for formatting dates. |
| `timeFormatLocale` | `String` | None | The locale (e.g. 'en_US' or 'fr_CA') to use for formatting time. |
| `numberFormat` | `NumberFormat` | None | The preference on how to format numbers when displaying them.  e.g. 1,234.56 vs 1.234,56 |
| `currencyFormat` | `CurrencyFormat` | None | The preference on where the currency symbol should be placed.  e.g. $123 vs 123$ |
| `firstDayOfWeek` | `Weekdays` | None | The day of week that is considered the first day of the week.  Usually SUN or MON. |

---

### PrivateLocationBiasInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `locationBiasingEnabled` | `Boolean` | None | - |
| `radius` | `Int` | None | - |

---

### PrivateMasterServiceGroupInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `I18nStringInput` | None | - |
| `order` | `Int` | None | - |
| `isArchived` | `Boolean` | None | - |
| `isMultiChoice` | `Boolean` | None | - |

---

### PrivateMasterServiceItemInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `I18nStringInput` | None | - |
| `description` | `I18nStringInput` | None | - |
| `educationDescription` | `I18nStringInput` | None | - |
| `duration` | `Int` | None | - |
| `amount` | `Int` | None | - |
| `type` | `MasterServiceItemType` | None | - |
| `externalUrl` | `String` | None | - |
| `order` | `Int` | None | - |
| `isDefault` | `Boolean` | None | - |
| `isTuning` | `Boolean` | None | - |
| `isTaxable` | `Boolean` | None | - |
| `isArchived` | `Boolean` | None | - |
| `isAnyUser` | `Boolean` | None | - |
| `isSelfSchedulable` | `Boolean` | None | - |
| `masterServiceGroupId` | `String` | None | - |
| `userIds` | `[String!]` | None | - |

---

### PrivateMergeClientsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `sourceClientId` | `String!` | None | - |
| `targetClientId` | `String!` | None | - |
| `pianoIdMapping` | `[PrivateMergePianosInput!]` | None | - |

---

### PrivateMergePianosInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `sourcePianoId` | `String!` | None | - |
| `targetPianoId` | `String!` | None | - |

---

### PrivateOnboardingInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `visible` | `Boolean` | None | - |
| `selectedTier` | `Int` | None | - |

---

### PrivatePianoInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `clientId` | `String` | None | - |
| `type` | `PianoType` | None | - |
| `make` | `String` | None | - |
| `model` | `String` | None | - |
| `serialNumber` | `String` | None | - |
| `location` | `String` | None | - |
| `status` | `PianoStatus` | None | - |
| `serviceIntervalMonths` | `Int` | None | - |
| `manualLastService` | `CoreDate` | None | - |
| `referenceId` | `String` | None | - |
| `useType` | `String` | None | - |
| `caseColor` | `String` | None | - |
| `caseFinish` | `String` | None | - |
| `year` | `Int` | None | - |
| `playerInstalled` | `Boolean` | None | - |
| `playerMake` | `String` | None | - |
| `playerModel` | `String` | None | - |
| `playerSerialNumber` | `String` | None | - |
| `damppChaserInstalled` | `Boolean` | None | - |
| `consignment` | `Boolean` | None | - |
| `rental` | `Boolean` | None | - |
| `rentalContractEndsOn` | `CoreDate` | None | - |
| `size` | `String` | None | - |
| `totalLoss` | `Boolean` | None | - |
| `needsRepairOrRebuilding` | `Boolean` | None | - |
| `lifecycleState` | `String` | None | - |
| `nextServiceOverride` | `CoreDate` | None | - |
| `damppChaserHumidistatModel` | `String` | None | - |
| `damppChaserMfgDate` | `CoreDate` | None | - |
| `hasIvory` | `Boolean` | None | - |
| `notes` | `String` | None | - |
| `primaryPianoPhotoId` | `String` | None | - |
| `potentialPerformanceLevel` | `Int` | None | - |
| `tags` | `[String!]` | None | A list of tags to apply to this piano.  If a tag does not exist, it will be created. |

---

### PrivatePianoMeasurementInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `pianoId` | `String` | None | - |
| `takenOn` | `CoreDate` | None | - |
| `humidity` | `Int` | None | - |
| `temperature` | `Int` | None | - |
| `a0Pitch` | `Int` | None | - |
| `a1Pitch` | `Int` | None | - |
| `a2Pitch` | `Int` | None | - |
| `a3Pitch` | `Int` | None | - |
| `a4Pitch` | `Int` | None | - |
| `a5Pitch` | `Int` | None | - |
| `a6Pitch` | `Int` | None | - |
| `a7Pitch` | `Int` | None | - |
| `a0Dip` | `Int` | None | - |
| `a1Dip` | `Int` | None | - |
| `a2Dip` | `Int` | None | - |
| `a3Dip` | `Int` | None | - |
| `a4Dip` | `Int` | None | - |
| `a5Dip` | `Int` | None | - |
| `a6Dip` | `Int` | None | - |
| `a7Dip` | `Int` | None | - |
| `d6SustainPlucked` | `Int` | None | - |
| `g6SustainPlucked` | `Int` | None | - |
| `c7SustainPlucked` | `Int` | None | - |
| `d6SustainPlayed` | `Int` | None | - |
| `g6SustainPlayed` | `Int` | None | - |
| `c7SustainPlayed` | `Int` | None | - |

---

### PrivatePianoPhotoInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `pianoId` | `String!` | None | - |
| `imageData` | `String!` | None | Base64 image file data. |
| `filename` | `String` | None | The file name.  If this isn't set, a name will be generated. |
| `notes` | `String` | None | - |
| `takenAt` | `CoreDateTime` | None | - |

---

### PrivatePianoPhotoUpdateInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `notes` | `String!` | None | - |

---

### PrivateQuickbooksAccountMappingInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `QuickbooksAccountType!` | None | - |
| `quickbooksAccountId` | `String!` | None | - |

---

### PrivateQuickbooksSyncInvoiceInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `invoiceId` | `String!` | None | - |

---

### PrivateRecommendationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `RecommendationType` | None | - |
| `name` | `I18nStringInput` | None | - |
| `explanation` | `I18nStringInput` | None | - |
| `isArchived` | `Boolean` | None | - |

---

### PrivateRecordCallCenterActionInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `contactKind` | `CallCenterContactKind!` | None | The type of contact made (email, called-human, called-message, sms, post-card, other) |
| `notes` | `String` | None | Optional notes about the contact |

---

### PrivateRemoteAccountingTaxMappingInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `RemoteAccountingType` | None | - |
| `taxes` | `[Tax!]` | None | - |
| `externalTaxId` | `String` | None | - |
| `isCaZeroPctRate` | `Boolean` | None | This is a flag indicates that this is that 0% tax rate to use for tips when syncing to QuickBooks Online.  This is only valid for Canadian companies. |

---

### PrivateRemoteCalendarInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `calendarDisplayName` | `String` | None | - |
| `availabilityImpactHandling` | `AvailabilityImpactHandling` | None | - |
| `importAsBusy` | `Boolean` | None | - |
| `sourceUrl` | `String` | None | - |

---

### PrivateRemoteCalendarIntegrationInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `String` | None | - |
| `type` | `RemoteCalendarIntegrationType` | None | - |
| `syncedGoogleCalendarIds` | `[String!]` | None | - |

---

### PrivateRenameTagInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `originalTag` | `ID!` | None | - |
| `newTag` | `String!` | None | - |
| `modelType` | `PrivateTagModelType!` | None | - |

---

### PrivateScheduledMessageInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `scheduledMessageTemplateId` | `String` | None | - |
| `clientId` | `String` | None | - |
| `language` | `String` | None | - |
| `type` | `ScheduledMessageType` | None | - |
| `subject` | `String` | None | - |
| `template` | `String` | None | - |
| `sendAt` | `CoreDateTime` | None | - |

---

### PrivateScheduledMessageTemplateInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `ScheduledMessageType` | None | - |
| `name` | `I18nStringInput` | None | - |
| `subject` | `I18nStringInput` | None | - |
| `template` | `I18nStringInput` | None | - |
| `order` | `Int` | None | - |

---

### PrivateSchedulerAvailabilityInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `name` | `String` | None | - |
| `serviceAreaId` | `String` | None | - |
| `startDate` | `CoreDate` | None | - |
| `endDate` | `CoreDate` | None | - |
| `startOfDayLocation` | `PrivateSchedulerLocationInput` | None | - |
| `startOfDayType` | `SchedulerStartOfDayType` | None | - |
| `startTime` | `String` | None | A time to start the day, in HH:MM format. |
| `endOfDayLocation` | `PrivateSchedulerLocationInput` | None | - |
| `endOfDayType` | `SchedulerEndOfDayType` | None | - |
| `endTime` | `String` | None | A time to end the day, in HH:MM format. |
| `recurrenceRule` | `String` | None | - |
| `includeDates` | `[CoreDate!]` | None | - |
| `excludeDates` | `[CoreDate!]` | None | - |
| `preferredSlotPolicy` | `SchedulerPreferredSlotPolicy` | None | - |
| `preferredSlotTimes` | `[String!]` | None | A list of preferred slots to offer (subject to the preferredSlotPolicy), in HH:MM format. |
| `adjustPreferredSlots` | `Boolean` | None | Whether or not to adjust preferred slot times to account for travel time.  For example, if you have an open day, start your day at home at 9am, have preferred slot times of 9:30am and 11am, and you have a 45 minute travel to an appointment, the 9:30am preferred_slot time will be excluded as a possibility unless this setting is set to true, shifting the 9:30am preferred slot to 9:45am to account for the 45 minutes of travel time from your home. |
| `isExclusive` | `Boolean` | None | - |
| `floatingDowntimeRules` | `[PrivateSchedulerFloatingDowntimeRuleInput!]` | None | - |
| `maxAppointmentsPerDay` | `Int` | None | The maximum number of appointments that can be scheduled in a day.  If this is not set, there is no limit. |
| `roundingMinutes` | `Int` | None | The number of minutes to round appointments to.  Valid values are 5, 10, 15, 30, and 60.  For example, a value of 15 will round to the top of the hour, 15 minutes after, 30, and 45.  If this is not set, we will use 5. |

---

### PrivateSchedulerCoordinatesInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `latitude` | `String!` | None | - |
| `longitude` | `String!` | None | - |

---

### PrivateSchedulerFloatingDowntimeRuleInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `startTime` | `String!` | None | - |
| `endTime` | `String!` | None | - |
| `duration` | `Int!` | None | - |

---

### PrivateSchedulerLocationInput

**Description:** A location that is used in defining a service area and availabilities.  If the type is an address, the addressLine field is required.  If the type is a coordinate, the coordinates field is required.  If the type is what3words, the what3words field is required.

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `SchedulerLocationType!` | None | - |
| `addressLine` | `String` | None | - |
| `coordinates` | `PrivateSchedulerCoordinatesInput` | None | - |
| `what3words` | `PrivateSchedulerWhat3wordsInput` | None | - |

---

### PrivateSchedulerPolygonParameterInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `shapes` | `[PrivateSchedulerShapeInput!]!` | None | - |

---

### PrivateSchedulerRadialParameterInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `center` | `PrivateSchedulerLocationInput!` | None | - |
| `travelTime` | `Int!` | None | - |

---

### PrivateSchedulerSelfScheduleMaxTravelTimeInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `daysFromToday` | `Int!` | None | - |
| `maxTravelTime` | `Int!` | None | - |

---

### PrivateSchedulerServiceAreaInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `algorithm` | `SchedulerServiceAreaAlgorithmType!` | None | - |
| `name` | `String!` | None | - |
| `polygonParameter` | `PrivateSchedulerPolygonParameterInput` | None | - |
| `radialParameter` | `PrivateSchedulerRadialParameterInput` | None | - |
| `buffer` | `Int!` | None | - |
| `selfScheduleMaxTravelTimes` | `[PrivateSchedulerSelfScheduleMaxTravelTimeInput!]!` | None | - |
| `travelMode` | `SchedulerTravelMode!` | None | - |
| `openDayWeight` | `Int!` | None | - |
| `includeTraffic` | `Boolean!` | None | - |
| `outsideServiceAreaMinutes` | `Int!` | None | - |
| `invalidAddressTravelTime` | `Int!` | None | - |
| `maxGoodTravelTimeMinutes` | `Int!` | None | - |
| `routingPreference` | `SchedulerRoutingPreferenceType!` | None | - |
| `isSelfSchedulable` | `Boolean!` | None | - |

---

### PrivateSchedulerShapeInput

**Description:** A shape that defines an area to be included or excluded from a service area.  If the type is a circle, the circleCenter, circleRadius, and circleRadiusUnit fields are required.  If the type is a polygon, the polygonPoints field is required.

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `type` | `SchedulerShapeType!` | None | - |
| `name` | `String` | None | - |
| `circleCenter` | `PrivateSchedulerCoordinatesInput` | None | - |
| `circleRadius` | `Float` | None | - |
| `circleRadiusUnit` | `SchedulerDistanceUnitType` | None | - |
| `polygonPoints` | `[PrivateSchedulerCoordinatesInput!]` | None | - |
| `inclusionMethod` | `SchedulerShapeInclusionMethod!` | None | - |

---

### PrivateSchedulerV2SearchInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `targetDate` | `CoreDate!` | None | - |
| `userIds` | `[String!]!` | None | - |
| `duration` | `Int!` | None | - |
| `addressLine` | `String` | None | - |
| `coordinates` | `PrivateCoordinatesInput` | None | - |
| `clientId` | `String` | None | The client ID being searched for.  This is simply used for logging and debugging purposes.  Pass it if you've got it. |

---

### PrivateSchedulerWhat3wordsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `what3words` | `String!` | None | - |

---

### PrivateSelectionInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `base` | `SelectionBase!` | None | - |
| `ids` | `[String!]` | None | - |

---

### PrivateSignupInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `countryCode` | `String` | None | - |
| `companyName` | `String` | None | - |
| `companyAddress` | `String` | None | - |
| `companyCity` | `String` | None | - |
| `companyState` | `String` | None | - |
| `companyZip` | `String` | None | - |
| `companyPhoneNumber` | `String` | None | - |
| `companyEmail` | `String` | None | - |
| `userFirstName` | `String` | None | - |
| `userLastName` | `String` | None | - |
| `userTimezone` | `String` | None | - |
| `userEmail` | `String` | None | - |
| `userPassword` | `String` | None | - |
| `userPasswordConfirmation` | `String` | None | - |
| `isGdprConsentGiven` | `Boolean` | None | - |
| `affiliateCode` | `String` | None | - |
| `planId` | `String` | None | - |
| `paymentMethodId` | `String` | None | - |
| `referralToken` | `String` | None | - |
| `companyWebsite` | `String` | None | - |

---

### PrivateUpdateBulkActionInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `emailOnCompletion` | `Boolean` | None | - |

---

### PrivateUpdateEstimateInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `contactId` | `String` | None | - |
| `assignedToId` | `String` | None | - |
| `pianoPhotoId` | `String` | None | - |
| `locale` | `String` | None | - |
| `notes` | `String` | None | - |
| `expiresOn` | `CoreDate` | None | - |
| `estimatedOn` | `CoreDate` | None | - |
| `currentPerformanceLevel` | `Float` | None | - |
| `isArchived` | `Boolean` | None | - |
| `tags` | `[String!]` | None | - |
| `pianoPotentialPerformanceLevel` | `Float` | None | - |
| `estimateTiers` | `[PrivateEstimateTierInput!]` | None | If this argument is present, all the tiers will be destroyed and recreated, so if you use this, pass ALL the tiers to recreate them. |

---

### PrivateUpdateInvoiceInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `contactId` | `String` | None | - |
| `assignedToId` | `String` | None | - |
| `dueOn` | `CoreDate` | None | - |
| `status` | `InvoiceStatus` | None | - |
| `notesHeader` | `String` | None | - |
| `notes` | `String` | None | - |
| `topNotesHeader` | `String` | None | - |
| `topNotes` | `String` | None | - |
| `netDays` | `Int` | None | - |
| `altBillingFirstName` | `String` | None | - |
| `altBillingLastName` | `String` | None | - |
| `altBillingCompanyName` | `String` | None | - |
| `altBillingStreet1` | `String` | None | - |
| `altBillingStreet2` | `String` | None | - |
| `altBillingMunicipality` | `String` | None | - |
| `altBillingRegion` | `String` | None | - |
| `altBillingPostalCode` | `String` | None | - |
| `altBillingCountryCode` | `String` | None | - |
| `altBillingEmail` | `String` | None | - |
| `altBillingPhone` | `String` | None | - |
| `summarize` | `Boolean` | None | - |
| `archived` | `Boolean` | None | - |
| `currencyCode` | `String` | None | - |
| `paymentAmount` | `Int` | None | - |
| `paymentType` | `InvoicePaymentType` | None | - |
| `paymentNotes` | `String` | None | - |
| `paymentTipAmount` | `Int` | None | - |
| `paymentPaidAt` | `CoreDateTime` | None | - |
| `acceptElectronicPayment` | `Boolean` | None | - |
| `acceptedElectronicPaymentMethods` | `[StripePaymentMethods!]` | None | - |
| `invoiceItems` | `[PrivateInvoiceItemInput!]` | None | - |
| `emailToAltBilling` | `Boolean` | None | - |
| `emailToContactEmailIds` | `[String!]` | None | - |
| `attachPdf` | `Boolean` | None | - |
| `emailSubject` | `String` | None | Custom email subject to use instead of the default |
| `emailMessage` | `String` | None | Custom email message to use instead of the template |
| `tags` | `[String!]` | None | - |

---

### PrivateUserFlagsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `makeMePreferredTechForNewClients` | `Boolean` | None | - |
| `hideDashboardReferralNotice` | `Boolean` | None | - |

---

### PrivateUserInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `firstName` | `String` | None | - |
| `lastName` | `String` | None | - |
| `calendarDefaultViewType` | `CalendarViewType` | None | - |
| `calendarDefaultTitleMode` | `CalendarTitleMode` | None | - |
| `calendarFontSize` | `CalendarFontSize` | None | - |
| `calendarDefaultShowAvailability` | `Boolean` | None | - |
| `calendarDefaultShowConfirmationWarnings` | `Boolean` | None | - |
| `calendarShowNonschedulableUsers` | `Boolean` | None | - |
| `calendarDefaultSendAppointmentConfirmation` | `Boolean` | None | - |
| `calendarShowDetailsOnIcsExport` | `Boolean` | None | - |
| `calendarIcsExportEventTypes` | `[EventType!]` | None | - |
| `calendarPromptToScheduleAfterCompletion` | `Boolean` | None | - |
| `calendarMakeCompletedAndPastEventsDimmer` | `Boolean` | None | - |
| `calendarShowCanceledAppointments` | `Boolean` | None | - |
| `uiExpandedTimeline` | `Boolean` | None | - |
| `calendarDefaultView` | `JSON` | None | - |
| `reservationNotificationsForSpecificUsers` | `[String!]` | None | - |
| `reservationNotificationsForAllUsers` | `Boolean` | None | - |
| `wantsReservationNotifications` | `Boolean` | None | - |
| `localizationId` | `String` | None | This sets the localization settings to use when displaying things to this user.  It should be an id from the allLocalizations listing. |
| `clientLocalizationId` | `String` | None | This sets the default localization to use for all clients who have this user set as their preferred technician.  Clients can override this default by having their own localization set explicitly, but this is a default in case they don't have one set. |
| `schedulable` | `Boolean` | None | - |
| `accessLevel` | `AccessLevel` | None | - |
| `hasLimitedAccess` | `Boolean` | None | - |
| `email` | `String` | None | - |
| `status` | `UserStatus` | None | - |
| `region` | `String` | None | - |
| `color` | `String` | None | - |
| `timezone` | `String` | None | - |
| `bufferTime` | `Int` | None | - |
| `makeMePreferredTechForNewClients` | `Boolean` | None | - |

---

### PrivateUserSettingsInput

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `scheduler` | `SchedulerSettings` | None | - |

---

### SchedulerSettings

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `errorReferenceId` | `String` | None | - |
| `longTermLimitDays` | `Int` | None | - |
| `shortTermLimitHours` | `Int` | None | - |
| `shortTermLimitHoursType` | `PrivateSchedulerShortTermLimitHoursType` | None | - |
| `shortTermLimitMessage` | `I18nStringInput` | None | - |
| `defaultTravelMode` | `SchedulerTravelMode` | None | - |

---

### Tax

**Champs:**

| Nom | Type | Défaut | Description |
|-----|------|--------|-------------|
| `rate` | `Int!` | None | - |
| `name` | `String!` | None | - |
| `id` | `String!` | None | - |

---

## Types Enum

### AccessLevel

**Valeurs:**

- `ADMIN`
- `TECHNICIAN`
- `ASSISTANT`

---

### ActiveOrHistorical

**Valeurs:**

- `ACTIVE`
- `HISTORICAL`

---

### AvailabilityImpactHandling

**Valeurs:**

- `NEVER_BUSY`: Synced events from remote calendar will never impact scheduling availability
- `ALWAYS_BUSY`: Synced events from remote calendar will always impact scheduling availability
- `OBEY_EVENT_BUSY_SETTING`: Synced events from remote calendar will impact scheduling availability based on the event's free/busy status

---

### AvailabilityLocationType

**Valeurs:**

- `HOME`: Start or end the day at home.  Using this, drive time home will be calculated and ensure you have enough time to arrive home by your end-of-day time (i.e. be home by 5pm).
- `CLIENT`: Start of end the day at a client's house.  Using this, drive time home will not be calculated at the start or end of your day.  i.e. Your day may end at 5pm at your client's house, and you still need to drive home.

---

### BulkActionStatus

**Valeurs:**

- `PENDING`
- `RUNNING`
- `SUCCESS`
- `PARTIAL_SUCCESS`
- `FAILED`

---

### BulkActionType

**Valeurs:**

- `ADD_CLIENT_TAG`
- `ADD_ESTIMATE_TAG`
- `MARK_APPOINTMENTS_COMPLETE`
- `ADD_INVOICE_TAG`
- `ADD_PIANO_TAG`
- `PAUSE_CLIENTS`
- `REMOVE_CLIENT_TAG`
- `REMOVE_ESTIMATE_TAG`
- `REMOVE_INVOICE_TAG`
- `REMOVE_PIANO_TAG`
- `CHANGE_CLIENT_STATUS`
- `CHANGE_PIANO_STATUS`
- `CLIENT_REMINDER_ASSIGNMENT`
- `CSV_EXPORT`
- `EXPORT_CLIENTS_TO_MAILCHIMP`
- `ARCHIVE_ESTIMATE`
- `ARCHIVE_INVOICE`
- `RECORD_CALL_CENTER_ACTION`

---

### BulkPauseClientsAction

**Valeurs:**

- `PAUSE`: Pause reminders for clients
- `UNPAUSE`: Unpause reminders for clients

---

### CalendarFontSize

**Valeurs:**

- `XSMALL`
- `SMALL`
- `NORMAL`
- `LARGE`
- `XLARGE`

---

### CalendarTitleMode

**Valeurs:**

- `TITLE`
- `TITLE_CITY`
- `TITLE_POSTAL_CODE`
- `POSTAL_CODE`
- `CITY`
- `NAME`
- `NAME_POSTAL_CODE`
- `NAME_CITY`
- `PIANOS`

---

### CalendarViewType

**Valeurs:**

- `MONTH`
- `WEEK`
- `DAY`
- `FOUR_DAY`

---

### CallCenterContactKind

**Valeurs:**

- `EMAIL`
- `CALLED_HUMAN`
- `CALLED_MESSAGE`
- `SMS`
- `POST_CARD`
- `OTHER`

---

### CallCenterItemSort

**Valeurs:**

- `DATE_ASC`
- `DATE_DESC`

---

### CallCenterReferenceType

**Valeurs:**

- `SCHEDULED_MESSAGE`
- `LIFECYCLE`

---

### ChangeMethod

**Valeurs:**

- `PERCENT_CHANGE`: Percent Change
- `SET_PRICE`: Set Price

---

### ClientLogStatus

**Valeurs:**

- `EMAILED`
- `CALLED_HUMAN`
- `CALLED_MESSAGE`
- `OTHER`
- `POST_CARD`
- `EMAIL`
- `TEXT`

---

### ClientLogType

**Valeurs:**

- `CLIENT`
- `COMMENT`
- `ESTIMATE`
- `INVOICE`
- `REMINDER`
- `PIANO`
- `SERVICE_ENTRY`

---

### ClientSort

**Valeurs:**

- `STATUS_ASC`
- `STATUS_DESC`
- `CLIENT_NAME_ASC`
- `CLIENT_NAME_DESC`
- `CREATED_AT_ASC`
- `CREATED_AT_DESC`
- `POSTAL_CODE_ASC`
- `POSTAL_CODE_DESC`
- `CITY_ASC`
- `CITY_DESC`
- `MUNICIPALITY_ASC`
- `MUNICIPALITY_DESC`
- `STATE_ASC`
- `STATE_DESC`
- `REGION_ASC`
- `REGION_DESC`

---

### ClientStatus

**Valeurs:**

- `ACTIVE`: An active client
- `INACTIVE`: An inactive client
- `PROSPECT`: A prospect client (one that has not yet scheduled an appointment)
- `NEW`: A new client (one that has scheduled an appointment, but that appointment hasn't happened yet)

---

### CompanyEmailTemplateType

**Valeurs:**

- `INVOICE_SUBJECT`
- `INVOICE`
- `SELF_SCHEDULE_CONFIRM_SUBJECT`
- `SELF_SCHEDULE_CONFIRM_MESSAGE`
- `RESERVATION_DECLINE_SUBJECT`
- `RESERVATION_DECLINE_MESSAGE`
- `APPOINTMENT_ADDED_SUBJECT`
- `APPOINTMENT_ADDED_MESSAGE`
- `APPOINTMENT_AUTO_DELETED_SUBJECT`
- `APPOINTMENT_AUTO_DELETED_MESSAGE`
- `APPOINTMENT_CONFIRMED_SUBJECT`
- `APPOINTMENT_CONFIRMED_MESSAGE`
- `ESTIMATE_SUBJECT`
- `ESTIMATE_MESSAGE`

---

### CompanyHeaderLayoutType

**Valeurs:**

- `SIDE_LOGO_WITH_NAME`
- `FULL_LOGO_WITHOUT_NAME`

---

### CompletionResultType

**Valeurs:**

- `COMPLETE`: An event that has been completed successfully
- `NO_SHOW`: An event that was a no-show (the client did not show up, no tuning was performed)
- `CANCELED`: An event that has been canceled (no tuning was performed)
- `OTHER`: The event was completed, but no tuning was performed

---

### ContactAddressType

**Valeurs:**

- `STREET`
- `MAILING`
- `BILLING`

---

### ContactLocationType

**Valeurs:**

- `ADDRESS`
- `COORDINATES`
- `WHAT3WORDS`

---

### ContactLocationUsageType

**Description:** The usage type of a contact location.  For example, a contact location may be used for mailing, billing, or street address.

**Valeurs:**

- `STREET`
- `MAILING`
- `BILLING`

---

### ContactsWithEmail

**Valeurs:**

- `NO_CONTACTS_HAVE_EMAIL`: No contacts for a client have an email address
- `ALL_CONTACTS_HAVE_EMAIL`: All contacts for a client have an email address
- `PRIMARY_CONTACT_HAS_EMAIL`: The primary contact for a client does not have an email address
- `PRIMARY_CONTACT_HAS_NO_EMAIL`: The primary contact for a client has an email address
- `BILLING_CONTACT_HAS_EMAIL`: The billing contact for a client has an email address
- `BILLING_CONTACT_HAS_NO_EMAIL`: The billing contact for a client does not have an email address

---

### ContactsWithPhone

**Valeurs:**

- `ALL_CONTACTS_HAVE_PHONE`: All contacts for a client have a phone number
- `NO_CONTACTS_HAVE_PHONE`: No contacts for a client have a phone number
- `PRIMARY_CONTACT_HAS_PHONE`: The primary contact for a client has a phone number
- `PRIMARY_CONTACT_HAS_NO_PHONE`: The primary contact for a client does not have a phone number
- `BILLING_CONTACT_HAS_PHONE`: The billing contact for a client has a phone number
- `BILLING_CONTACT_HAS_NO_PHONE`: The billing contact for a client does not have a phone number

---

### ContactsWithTextablePhone

**Valeurs:**

- `NO_CONTACTS_HAVE_TEXTABLE_PHONE`: No contacts for a client have a confirmed textable phone number
- `ALL_CONTACTS_HAVE_TEXTABLE_PHONE`: All contacts for a client have a confirmed textable phone number
- `PRIMARY_CONTACT_HAS_TEXTABLE_PHONE`: The primary contact for a client has a confirmed textable phone number
- `PRIMARY_CONTACT_HAS_NO_TEXTABLE_PHONE`: The primary contact for a client does not have a confirmed textable phone number
- `BILLING_CONTACT_HAS_TEXTABLE_PHONE`: The billing contact for a client has a confirmed textable phone number
- `BILLING_CONTACT_HAS_NO_TEXTABLE_PHONE`: The billing contact for a client does not have a confirmed textable phone number

---

### CurrencyFormat

**Description:** This is where to put the currency symbol.

**Valeurs:**

- `BEFORE`: Currency formatted like $123
- `AFTER`: Currency formatted like 123$

---

### DriveTimeErrorType

**Valeurs:**

- `GENERIC_ERROR`
- `NETWORK_ERROR`
- `NOT_FOUND`
- `ORIGIN_NOT_FOUND`
- `DESTINATION_NOT_FOUND`
- `NOT_SUPPORTED`

---

### EmailStatus

**Valeurs:**

- `ACCEPTED`
- `BOUNCED`
- `CLICKED`
- `COMPLAINED`
- `DELIVERED`
- `DROPPED`
- `FAILED`
- `OPENED`
- `PENDING`
- `UNSUBSCRIBED`
- `UNDELIVERED`
- `QUEUED`
- `SENT`

---

### EmailSubscriptionType

**Valeurs:**

- `NORMAL`
- `UNSUBSCRIBE`
- `BOUNCE`
- `SPAM_COMPLAINT`

---

### ErrorLogSort

**Valeurs:**

- `CREATED_AT_ASC`
- `CREATED_AT_DESC`

---

### ErrorLogType

**Valeurs:**

- `SCHEDULED_MESSAGE`
- `EMAIL_UNSUBSCRIBE`
- `EMAIL_COMPLAINT`
- `BAD_EMAIL_ADDRESS`
- `SMS_UNSUBSCRIBE`
- `FAILED_PAYMENT`

---

### ErrorType

**Valeurs:**

- `GENERIC`
- `ACCESS_DENIED`
- `VALIDATION`
- `NOT_FOUND`

---

### EstimateSort

**Valeurs:**

- `NUMBER_ASC`
- `NUMBER_DESC`
- `CREATED_AT_ASC`
- `CREATED_AT_DESC`
- `RECOMMENDED_TIER_TOTAL_ASC`
- `RECOMMENDED_TIER_TOTAL_DESC`
- `PRIMARY_TIER_TOTAL_ASC`
- `PRIMARY_TIER_TOTAL_DESC`
- `CLIENT_NAME_ASC`
- `CLIENT_NAME_DESC`
- `EXPIRES_ON_ASC`
- `EXPIRES_ON_DESC`
- `ESTIMATED_ON_ASC`
- `ESTIMATED_ON_DESC`

---

### EventCancelNoticeStatus

**Valeurs:**

- `OPEN`
- `DISMISSED`
- `DELETED`

---

### EventConfirmationWarning

**Valeurs:**

- `NONE`: No warning about the confirmation should be displayed.
- `NOTICE`: The appointment is close, the company requires confirmations, and the client has not yet confirmed.
- `CRITICAL`: The appointment is VERY close, the company requires confirmations, and the client has not yet confirmed.

---

### EventLocationType

**Valeurs:**

- `ADDRESS`
- `COORDINATES`
- `WHAT3WORDS`
- `SINGLE_LINE_ADDRESS`

---

### EventRecurrenceChangeType

**Valeurs:**

- `SELF`
- `FUTURE`

---

### EventRecurrenceEndingType

**Valeurs:**

- `OCCURRENCES`
- `DATE`

---

### EventRecurrenceType

**Valeurs:**

- `WEEKLY`
- `MONTHLY`

---

### EventReservationSort

**Valeurs:**

- `STARTS_AT_ASC`
- `STARTS_AT_DESC`
- `CREATED_AT_ASC`
- `CREATED_AT_DESC`
- `PENDING_FIRST`
- `PENDING_LAST`

---

### EventReservationSource

**Valeurs:**

- `CLIENT_SCHEDULE`

---

### EventReservationStatus

**Valeurs:**

- `PENDING`
- `DECLINED`
- `APPROVED`

---

### EventReservationType

**Valeurs:**

- `APPOINTMENT`

---

### EventSort

**Valeurs:**

- `START_ASC`
- `START_DESC`
- `EVENT_NEAR_TODAY_ASC`
- `EVENT_NEAR_TODAY_DESC`
- `USER_LAST_NAME_ASC`
- `USER_LAST_NAME_DESC`

---

### EventStatus

**Valeurs:**

- `ACTIVE`
- `CANCELED`
- `NO_SHOW`
- `COMPLETE`

---

### EventType

**Valeurs:**

- `APPOINTMENT`
- `PERSONAL`
- `MEMO`
- `SYNCED`

---

### GazelleReferralStatus

**Valeurs:**

- `PAID_OUT`
- `SENT`
- `CLICKED`
- `SIGNED_UP`
- `SIGNED_UP_PAID_1`
- `SIGNED_UP_PAID_2`
- `SIGNED_UP_PAID_3`

---

### GeocodeLocationType

**Valeurs:**

- `ROOFTOP`
- `RANGE_INTERPOLATED`
- `GEOMETRIC_CENTER`
- `APPROXIMATE`
- `ADDRESS_NOT_FOUND`
- `UNKNOWN`

---

### HeaderLayout

**Valeurs:**

- `SIDE_LOGO_WITH_NAME`: Show the logo smaller on the side and render the company name beside it and the app name below that.
- `FULL_LOGO_WITHOUT_NAME`: Show the logo big above the app name, but do not show the company name.

---

### InvoiceItemType

**Valeurs:**

- `LABOR_FIXED_RATE`
- `LABOR_HOURLY`
- `EXPENSE`
- `MILEAGE`
- `OTHER`
- `LEGACY_GROUP`

---

### InvoicePaymentSource

**Valeurs:**

- `MANUAL`
- `STRIPE`
- `QUICKBOOKS_ONLINE`

---

### InvoicePaymentStatus

**Valeurs:**

- `CANCELED`
- `DISPUTED`
- `FAILED`
- `PROCESSING`
- `REFUNDED`
- `SUCCEEDED`
- `REQUIRES_PAYMENT_METHOD`
- `REQUIRES_CONFIRMATION`
- `REQUIRES_ACTION`
- `REQUIRES_CAPTURE`

---

### InvoicePaymentType

**Valeurs:**

- `CASH`
- `CHECK`
- `CREDIT_CARD`
- `DEBIT_CARD`
- `ACH`
- `ELECTRONIC_FUNDS_TRANSFER`
- `OTHER`
- `PAYPAL`
- `SEPA`
- `VENMO`
- `ZELLE`
- `BANCONTACT`
- `EPS`
- `GIROPAY`
- `IDEAL`
- `SOFORT`
- `P24`

---

### InvoiceSort

**Valeurs:**

- `NUMBER_ASC`
- `NUMBER_DESC`
- `STATUS_ASC`
- `STATUS_DESC`
- `CREATED_AT_ASC`
- `CREATED_AT_DESC`
- `TOTAL_ASC`
- `TOTAL_DESC`
- `DUE_TOTAL_ASC`
- `DUE_TOTAL_DESC`
- `INVOICE_DATE_ASC`
- `INVOICE_DATE_DESC`
- `DUE_DATE_ASC`
- `DUE_DATE_DESC`
- `CLIENT_NAME_ASC`
- `CLIENT_NAME_DESC`

---

### InvoiceStatus

**Valeurs:**

- `DRAFT`
- `OPEN`
- `OVERDUE`
- `PAID`
- `DELETED`
- `CANCELED`

---

### LegalContractType

**Valeurs:**

- `EU_GDPR_DPA`
- `UK_GDPR_DPA`

---

### LifecycleSort

**Valeurs:**

- `NAME_ASC`
- `NAME_DESC`
- `CREATED_AT_ASC`
- `CREATED_AT_DESC`

---

### LifecycleState

**Valeurs:**

- `NO_LIFECYCLE`
- `PROSPECT`
- `NEW`
- `INACTIVE`
- `ACTIVE`
- `WITHOUT_SCHEDULING_DETAILS`
- `TUNING_SCHEDULED`
- `NOT_DUE`
- `COMING_DUE`
- `DUE`
- `OVERDUE_STAGE_1`
- `OVERDUE_STAGE_2`
- `OVERDUE_STAGE_3`
- `COMPLETE`
- `NO_SHOW`
- `CANCELED`
- `PAST`
- `TODAY`
- `CONFIRMED`
- `UNCONFIRMED`
- `UNCONFIRMED_CRITICAL`
- `FUTURE`

---

### LifecycleType

**Valeurs:**

- `CLIENT`
- `PIANO`
- `EVENT`

---

### LocationType

**Valeurs:**

- `ADDRESS`
- `COORDINATES`
- `WHAT3WORDS`

---

### MappingProviderType

**Valeurs:**

- `GOOGLE`
- `AZURE`
- `MAPBOX`
- `AWS_HERE`

---

### MasterServiceItemType

**Valeurs:**

- `LABOR_FIXED_RATE`: Labor Fixed Rate
- `LABOR_HOURLY`: Labor Hourly
- `EXPENSE`: Expense
- `MILEAGE`: Mileage
- `OTHER`: Other

---

### NumberFormat

**Description:** This is how numbers should be formatted for display.

**Valeurs:**

- `COMMA_DECIMAL_THREE`: Numbers formatted like 12,345,678.91
- `DECIMAL_COMMA_THREE`: Numbers formatted like 12.345.678,91
- `SPACE_COMMA_THREE`: Numbers formatted like 12 345 678,91

---

### ParkedCompanyReason

**Valeurs:**

- `NOT_PARKED`
- `PARKED_MANUALLY`
- `CARD_EXPIRED`
- `NO_CARD`
- `UNPAID`
- `UNABLE_TO_CHARGE`
- `OVER_PIANO_LIMIT`
- `NO_SUBSCRIPTION`
- `UNKNOWN`

---

### PhoneClass

**Valeurs:**

- `MOBILE`
- `LANDLINE`
- `VOIP`
- `UNKNOWN`

---

### PhoneFormat

**Valeurs:**

- `NATIONAL`
- `INTERNATIONAL`
- `E164`

---

### PhoneType

**Valeurs:**

- `UNKNOWN`
- `PRIMARY`
- `SECONDARY`
- `MOBILE`
- `HOME`
- `WORK`
- `FAX`

---

### PhotoSort

**Valeurs:**

- `CREATED_AT_ASC`
- `CREATED_AT_DESC`

---

### PianoSort

**Valeurs:**

- `STATUS_ASC`
- `STATUS_DESC`
- `LAST_SERVICE_ASC`
- `LAST_SERVICE_DESC`
- `NEXT_SERVICE_ASC`
- `NEXT_SERVICE_DESC`
- `NEXT_SCHEDULED_TUNING_ASC`
- `NEXT_SCHEDULED_TUNING_DESC`
- `DUE_NEAR_TODAY_ASC`: The due near today sorting mechanism puts pianos that are due closest to today (before or after) at the top, and the further away from today they are (before or after), the further down the list they will be.
- `DUE_NEAR_TODAY_DESC`: The due near today sorting mechanism puts pianos that are due closest to today (before or after) at the top, and the further away from today they are (before or after), the further down the list they will be.
- `CREATED_AT_ASC`
- `CREATED_AT_DESC`
- `MAKE_ASC`
- `MAKE_DESC`
- `MODEL_ASC`
- `MODEL_DESC`

---

### PianoStatus

**Valeurs:**

- `ACTIVE`
- `INACTIVE`
- `TEMPORARY_STORAGE`
- `UNDER_RESTORATION`

---

### PianoType

**Valeurs:**

- `UNKNOWN`
- `GRAND`
- `SQUARE_GRAND`
- `SPINET`
- `STUDIO`
- `UPRIGHT`
- `CONSOLE`
- `DIGITAL`
- `ORGAN`
- `HARPSICHORD`
- `FORTEPIANO`
- `CLAVICHORD`
- `AUTOHARP`
- `HYBRID`

---

### PricingModel

**Valeurs:**

- `JAKKLOPS`
- `TOMOODE`

---

### PricingModelInterval

**Valeurs:**

- `MONTH`
- `YEAR`

---

### PrivateJakklopsPricingFeatureType

**Valeurs:**

- `CORE`
- `REMINDERS`
- `SMS`
- `SCHEDULING`
- `INVOICES`
- `ESTIMATES`
- `QUICKBOOKS`
- `MAILCHIMP`

---

### PrivateSchedulerShortTermLimitHoursType

**Valeurs:**

- `HARD`
- `SOFT`

---

### PrivateTagModelType

**Valeurs:**

- `CLIENT`
- `PIANO`
- `INVOICE`
- `ESTIMATE`

---

### QuickbooksAccountType

**Valeurs:**

- `UNDEPOSITED_FUNDS`
- `BANK_ACCOUNT_REGISTER`
- `STRIPE_PROCESSING_FEES`
- `CLEARING_ACCOUNT`

---

### QuickbooksBatchSyncStatus

**Valeurs:**

- `NOT_STARTED`
- `RUNNING_INVOICE_SYNC`
- `RUNNING_STRIPE_PAYOUT_SYNC`
- `RUNNING_QBO_PAYMENT_SYNC`
- `ERROR`
- `COMPLETE`
- `EARLY_SHUTDOWN`

---

### QuickbooksSupportLevel

**Valeurs:**

- `PRODUCTION`
- `BETA`

---

### QuickbooksSyncErrorType

**Valeurs:**

- `QBO_DISCONNECTED`
- `MISSING_TAX_MAPPINGS`
- `QBO_TAX_RATE_NOT_FOUND`
- `INVOICE_LINES_TAX_MISMATCH`
- `TAX_RATE_MISMATCH`
- `CURRENCY_MISMATCH`
- `INVOICE_TOTAL_MISMATCH`
- `STRIPE_AND_QBO_CURRENCY_MISMATCH`
- `MISSING_ACCOUNT_MAPPINGS`
- `STRIPE_PAYMENT_NOT_IN_GAZELLE`
- `STRIPE_PAYMENT_NOT_YET_SYNCED`
- `MISSING_CA_ZERO_PCT_RATE_TAX_MAPPING`
- `STRIPE_INSTANT_PAYOUT_NOT_SYNCED`
- `UNKNOWN`

---

### QuickbooksSyncNoticeType

**Valeurs:**

- `TAX_MISMATCH`
- `UNKNOWN`

---

### QuickbooksSyncStatus

**Valeurs:**

- `NOT_STARTED`
- `RUNNING`
- `ERROR`
- `SUCCESS`
- `EARLY_SHUTDOWN`

---

### RecommendationType

**Valeurs:**

- `YES`
- `NO`
- `MAYBE`

---

### ReminderType

**Valeurs:**

- `EMAIL`
- `CALL`
- `SMS`

---

### RemoteAccountingType

**Valeurs:**

- `QUICKBOOKS`

---

### RemoteCalendarIntegrationType

**Valeurs:**

- `GAZELLE`
- `GOOGLE`
- `ICS`

---

### ReservationCompleteBehavior

**Valeurs:**

- `NONE`
- `SHOW_LINK`
- `REDIRECT`

---

### SMSVerificationStatus

**Description:** The status of SMS verification for a company

**Valeurs:**

- `PENDING`: Verification is pending review
- `APPROVED`: Verification has been approved

---

### ScheduledMessageType

**Valeurs:**

- `EMAIL`
- `CALL`
- `SMS`

---

### SchedulerDistanceUnitType

**Valeurs:**

- `MILES`
- `KILOMETERS`

---

### SchedulerEndOfDayType

**Valeurs:**

- `END_OF_DAY_LOCATION`
- `CLIENT`

---

### SchedulerLocationType

**Valeurs:**

- `ADDRESS`
- `COORDINATES`
- `WHAT3WORDS`

---

### SchedulerPreferredSlotPolicy

**Valeurs:**

- `ONLY_OPEN_DAY`
- `ONLY_PREFERRED_SLOTS`
- `COMBINED`

---

### SchedulerRoutingPreferenceType

**Valeurs:**

- `PROXIMITY`
- `ALONG_ROUTES`

---

### SchedulerServiceAreaAlgorithmType

**Valeurs:**

- `POLYGON`
- `RADIAL`

---

### SchedulerShapeInclusionMethod

**Valeurs:**

- `INCLUDE`
- `EXCLUDE`

---

### SchedulerShapeType

**Valeurs:**

- `POLYGON`
- `CIRCLE`

---

### SchedulerSlotFilterReasonType

**Valeurs:**

- `OUTSIDE_LONG_TERM_LIMIT`
- `OUTSIDE_SERVICE_AREA`
- `AVAILABILITY_TIME`
- `OVERLAPS_EXISTING_SLOT`
- `OUTSIDE_SHORT_TERM_LIMIT`
- `VIOLATES_FLOATING_DOWNTIME_RULE`
- `MAX_APPOINTMENTS_PER_DAY`
- `SELF_SCHEDULE_MAX_TRAVEL_TIMES`
- `UNABLE_TO_ROUND_START_TIME`
- `DUPLICATE_STARTS_AT`
- `NOT_ENOUGH_TRAVEL_TIME`
- `SUFFICIENT_SLOTS_FOUND`
- `IMPOSSIBLE_DISTANCE`
- `TOO_MANY_OUTSIDE_SERVICE_AREA`
- `IN_PAST_OR_EXTREME_NEAR_FUTURE`
- `CHANGED_DATE`

---

### SchedulerSlotFlagType

**Valeurs:**

- `OUTSIDE_SERVICE_AREA`
- `OUTSIDE_SHORT_TERM_LIMIT`
- `OUTSIDE_LONG_TERM_LIMIT`
- `NEARBY_EXISTING_EVENT`
- `SELF_SCHEDULE_MAX_TRAVEL_TIMES`
- `NO_ROUTE_BEFORE`
- `NO_ROUTE_AFTER`

---

### SchedulerStartOfDayType

**Valeurs:**

- `START_OF_DAY_LOCATION`
- `CLIENT`

---

### SchedulerTravelMode

**Valeurs:**

- `DRIVING`
- `WALKING`
- `BICYCLING`
- `TRANSIT`

---

### SelectionBase

**Valeurs:**

- `ALL`
- `NONE`

---

### SelfConfirmedAppointmentSort

**Valeurs:**

- `CONFIRMED_AT_ASC`
- `CONFIRMED_AT_DESC`

---

### SentOrScheduledMessageDeliveryType

**Valeurs:**

- `EMAIL`
- `SMS`
- `CALL`

---

### SentOrScheduledMessageRelatedType

**Valeurs:**

- `EMAIL`
- `SMS`
- `SCHEDULED_MESSAGE`

---

### SentOrScheduledMessageSort

**Valeurs:**

- `SENT_OR_SCHEDULED_AT_ASC`
- `SENT_OR_SCHEDULED_AT_DESC`

---

### SentOrScheduledMessageSource

**Valeurs:**

- `INVOICE`
- `ESTIMATE`

---

### SentOrScheduledMessageStatus

**Valeurs:**

- `ACCEPTED`
- `BOUNCED`
- `CLICKED`
- `COMPLAINED`
- `DELIVERED`
- `DROPPED`
- `FAILED`
- `OPENED`
- `PENDING`
- `UNSUBSCRIBED`
- `UNDELIVERED`
- `QUEUED`
- `SENT`
- `RECEIVED`
- `SCHEDULED`

---

### SentOrScheduledMessageType

**Valeurs:**

- `SENT`
- `SCHEDULED`

---

### SmsStatus

**Valeurs:**

- `ACCEPTED`
- `SENT`
- `FAILED`
- `DELIVERED`
- `RECEIVED`
- `QUEUED`
- `UNDELIVERED`

---

### StripePaymentMethods

**Valeurs:**

- `CARD`
- `SEPA_DEBIT`
- `ACH`
- `BANCONTACT`
- `EPS`
- `GIROPAY`
- `IDEAL`
- `SOFORT`
- `P24`

---

### SubscriptionStatus

**Valeurs:**

- `ACTIVE`
- `PAST_DUE`
- `UNPAID`
- `CANCELED`
- `INCOMPLETE`
- `INCOMPLETE_EXPIRED`
- `TRIALING`

---

### SystemNotificationAlertType

**Valeurs:**

- `ERROR`
- `WARNING`
- `INFO`

---

### SystemNotificationSort

**Valeurs:**

- `CREATED_AT_ASC`
- `CREATED_AT_DESC`

---

### SystemNotificationSubType

**Valeurs:**

- `FAILED_PAYMENT`
- `TRIAL_ENDING`
- `CALENDAR_INTEGRATION`
- `AUTHORIZATION_ERROR`
- `SYNC_ERROR`
- `NEEDS_SIGNATURE`

---

### SystemNotificationType

**Valeurs:**

- `BILLING`
- `CALENDAR_INTEGRATION`
- `QUICKBOOKS_INTEGRATION`
- `LEGAL_CONTRACT`

---

### TechnicianSelectionBehavior

**Valeurs:**

- `ANY`
- `PREFERRED_TECHNICIAN`
- `HIDDEN`

---

### TimelineEntryType

**Valeurs:**

- `CONTACT_EMAIL_AUTOMATED`: An email message that was sent through Gazelle.  Could be a reminder, and invoice, and appointment notice, etc.
- `CONTACT_EMAIL_MANUAL`: An email that the user sent manually.  This is used when the user manually says that they emailed the client.
- `CONTACT_SMS_AUTOMATED`: A text message that was sent through Gazelle.  Could be a reminder, and invoice, and appointment notice, etc.
- `CONTACT_SMS_MANUAL`: A text message that the user sent manually.  This is used when the user manually says that they texted the client.
- `CONTACT_PHONE_AUTOMATED`: RESERVED FOR FUTURE USE
- `CONTACT_PHONE_MANUAL_TALKED`: A phone call that the user made themselves.  This one means they actually reached a person and talked with them.
- `CONTACT_PHONE_MANUAL_MESSAGE`: A phone call that the user made themselves.  This one means they were unable to reach a person, but left a message.
- `CONTACT_POST_AUTOMATED`: RESERVED FOR FUTURE USE
- `CONTACT_POST_MANUAL`: A physical postal mailing that the user made themselves.  Usually this means they sent a postcard or a letter.
- `CONTACT_OTHER_MANUAL`: Some other form of contact that is not email, sms, phone, or post, that the user did manually themselves.
- `ERROR_MESSAGE`: An error that occurred at some point for this client.  This is often a problem with sending a reminder or validating an address, etc.
- `SYSTEM_MESSAGE`: Some kind of generic system message.  This is usually some kind of log message to indicate that something important happened like an appointment was rescheduled, etc.
- `USER_COMMENT`: A comment that a user left on this client's timeline.
- `SERVICE_ENTRY_AUTOMATED`: This is a note about service that was performed on a piano.  This one is logged automatically by Gazelle, usually coming from invoice items.
- `SERVICE_ENTRY_MANUAL`: This is a note about service that was performed on a piano.  This entry was manually made by the technician, it's like a USER_COMMENT, but for a specific piano.
- `APPOINTMENT`: An appointment with a client
- `APPOINTMENT_LOG`: RESERVED FOR FUTURE USE
- `INVOICE`: An invoice that was created for a client.
- `INVOICE_LOG`: A log message associated with an invoice, like payment received, etc.
- `INVOICE_PAYMENT`: An invoice payment.
- `INVOICE_SYNC`: The invoice was synced to a third party accounting system.
- `PIANO_MEASUREMENT`: A measurement associated with an invoice (temperature, humidity, etc).
- `SCHEDULED_MESSAGE_EMAIL`: An email message scheduled to be sent in the future through Gazelle.
- `SCHEDULED_MESSAGE_SMS`: A text message scheduled to be sent in the future through Gazelle.
- `SCHEDULED_MESSAGE_PHONE`: A phone call reminder that is scheduled to appear in the future in the call center.
- `ESTIMATE`: An estimate that was created for a client.
- `ESTIMATE_LOG`: A log message associated with an estimate, like email sent, etc.
- `SYSTEM_NOTIFICATION`: A error, warning, or informational message.  This may be related to a client, piano, invoice, or estimate.

---

### UserPaymentOption

**Valeurs:**

- `STRIPE`
- `MANUAL`

---

### UserStatus

**Valeurs:**

- `ACTIVE`: An active user
- `INACTIVE`: An inactive user

---

### Weekdays

**Valeurs:**

- `SUN`
- `MON`
- `TUE`
- `WED`
- `THU`
- `FRI`
- `SAT`

---
