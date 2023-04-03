// Copyright 2023, Ayon, All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "OPActionResult.generated.h"

/**
 * @brief This macro returns error code when is problem or does nothing when there is no problem.
 * @param ActionResult FOP_ActionResult structure
 */
#define EVALUATE_OP_ACTION_RESULT(ActionResult) \
	if(ActionResult.IsProblem()) \
		return ActionResult.GetStatus();

/**
* @brief This enum values are humanly readable mapping of error codes.
* Here should be all error codes to be possible find what went wrong.
* TODO: In the future a web document should exists with the mapped error code & what problem occurred & how to repair it...
*/
UENUM()
namespace EOP_ActionResult
{
	enum Type
	{
		Ok,
		ProjectNotCreated,
		ProjectNotLoaded,
		ProjectNotSaved,
		//....Here insert another values

		//Do not remove!
		//Usable for looping through enum values
		__Last UMETA(Hidden)
	};
}


/**
 * @brief This struct holds action result enum and optionally reason of fail
 */
USTRUCT()
struct FOP_ActionResult
{
	GENERATED_BODY()

public:
	/**	 @brief Default constructor usable when there is no problem */
	FOP_ActionResult();

	/**
	 * @brief This constructor initializes variables & attempts to log when is error
	 * @param InEnum Status
	 */
	FOP_ActionResult(const EOP_ActionResult::Type& InEnum);

	/**
	 * @brief This constructor initializes variables & attempts to log when is error
	 * @param InEnum Status
	 * @param InReason Reason of potential fail
	 */
	FOP_ActionResult(const EOP_ActionResult::Type& InEnum, const FText& InReason);

private:
	/** @brief Action status  */
	EOP_ActionResult::Type Status;

	/** @brief Optional reason of fail	 */
	FText Reason;

public:
	/**
	 * @brief Checks if there is problematic state
	 * @return true when status is not equal to EOP_ActionResult::Ok
	 */
	bool IsProblem() const;
	EOP_ActionResult::Type& GetStatus();
	FText& GetReason();

private:
	void TryLog() const;
};

