package model

import (
	"time"

	"gorm.io/datatypes"
	"gorm.io/gorm"
)

type Group struct {
	gorm.Model
	InstanceID string `json:"instance_id"`
	JID        string `json:"jid" gorm:"uniqueIndex"`
	OwnerJID   string `json:"owner_jid"`
	Name       string `json:"name"`
	Topic      string `json:"topic"`
	// Store participants as a JSON string in the database
	Participants datatypes.JSON `json:"participants"`
}

type Participant struct {
	JID          string `json:"jid"`
	IsAdmin      bool   `json:"is_admin"`
	IsSuperAdmin bool   `json:"is_super_admin"`
}

type GroupInfo struct {
	JID                       string        `json:"jid"`
	OwnerJID                  string        `json:"owner_jid"`
	Name                      string        `json:"name"`
	NameSetAt                 time.Time     `json:"name_set_at"`
	NameSetBy                 string        `json:"name_set_by"`
	Topic                     string        `json:"topic"`
	TopicID                   string        `json:"topic_id"`
	TopicSetAt                time.Time     `json:"topic_set_at"`
	TopicSetBy                string        `json:"topic_set_by"`
	TopicDeleted              bool          `json:"topic_deleted"`
	IsLocked                  bool          `json:"is_locked"`
	IsAnnounce                bool          `json:"is_announce"`
	AnnounceVersionID         string        `json:"announce_version_id"`
	IsEphemeral               bool          `json:"is_ephemeral"`
	DisappearingTimer         uint32        `json:"disappearing_timer"`
	IsIncognito               bool          `json:"is_incognito"`
	IsParent                  bool          `json:"is_parent"`
	DefaultMembershipApproval string        `json:"default_membership_approval_mode"`
	LinkedParentJID           string        `json:"linked_parent_jid"`
	IsDefaultSubGroup         bool          `json:"is_default_sub_group"`
	IsJoinApprovalRequired    bool          `json:"is_join_approval_required"`
	GroupCreated              time.Time     `json:"group_created"`
	ParticipantVersionID      string        `json:"participant_version_id"`
	Participants              []Participant `json:"participants"`
	MemberAddMode             string        `json:"member_add_mode"`
}
